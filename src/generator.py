#!/usr/bin/env python3

import os
from collections import defaultdict

from .classes.Localisation import Localisation
from .classes.Rule import Rule
from .classes.RuleEntry import RuleEntry
from .core.constants import (
    GLOBAL_DECISION_KEYS,
    LOCALISATION_ENCODING,
    ON_ACTION_TRIGGERS,
)
from .defines.paths import *
from .defines.templates import *
from .defines.game_config import *
from .core.file_helpers import (
    build_decisions_file_path,
    build_event_file_path,
    build_global_localisation_file_path,
    build_localisation_file_path,
    build_master_event_file_path,
    build_on_actions_file_path,
    ensure_directory,
    write_file_with_directory,
)
from .core.logging_utils import (
    log_master,
    log_module,
    log_product,
    print_duplicate_keys_summary,
    print_final_statistics,
)
from .utils import *


class Generator:
    """Top-level generator that iterates over modules and builds Product instances.

    Responsibilities:
    - Iterate all module pairs in modules_root
    - Create Product(module_1, module_2), build it and collect its localisation keys
    - Write a master dispatcher event file that references all per-product events
    - Fail if any localisation key is generated more than once across products

    Contains:
    - Product: Inner class for managing individual localisation products
    """

    def __init__(self, modules_root: str):
        self.modules_root = modules_root
        self.module_names = sorted(os.listdir(modules_root))
        self.generated_keys: dict[str, str] = {}  # key -> product event_name
        self.duplicate_keys: dict[str, list[str]] = (
            {}
        )  # key -> list of products that generated it
        self.triggers: list[str] = []

    def _register_product_keys(self, event_name: str, keys: set[str]):
        """Register keys from a product and check for duplicates."""
        for k in keys:
            if k in self.generated_keys:
                other = self.generated_keys[k]
                self._log_duplicate_warning(k, event_name, other)

                # Track all products that generate this key
                if k not in self.duplicate_keys:
                    self.duplicate_keys[k] = [other]
                self.duplicate_keys[k].append(event_name)
            else:
                self.generated_keys[k] = event_name

    class Product:
        """Manage a single localisation/product for a pair of modules.

        Responsibilities:
        - Load tag names, dynasties and rules for the two modules
        - Build rules -> RuleEntry mappings
        - Generate event script file for this product
        - Generate localisation file and register keys with parent Generator
        """

        def __init__(self, generator: "Generator", module_1: str, module_2: str):
            self.generator = generator
            self.module_1 = module_1
            self.module_2 = module_2
            self.module_1_path = os.path.join(MODULES_ROOT, module_1)
            self.module_2_path = os.path.join(MODULES_ROOT, module_2)
            self.event_name = f"{EVENT_NAME}_{module_1.lower()}_{module_2.lower()}"

            # Load data
            self.tag_name_list = read_tag_names(self._get_tag_names_path())
            self._log_module(module_2, "Tag names read successfully")
            self.dynasty_names = read_lines(self._get_dynasties_path())
            self._log_module(module_2, "Dynasty names read successfully")
            self.rules_list: list[Rule] = parse_rules_dir(self._get_rules_dir())
            self._log_module(module_1, "Rules read successfully")
            self.substitution_rules_list: list[Rule] = parse_rules_dir(
                self._get_sub_rules_dir()
            )
            self._log_module(module_2, "Substitution rules read successfully")

            # Validate loaded data
            self._validate_required_data()

            # Working data
            self.global_rules_list: list[Rule] = []
            self.tagged_rules_list: list[Rule] = []
            self.rules: dict[str, list[RuleEntry]] = defaultdict(list)
            self.tag_to_rules: dict[str, list[Rule]] = defaultdict(list)
            self.events = {}
            self.event_id = 1

            # helper mappings so we can find the original Rule from a RuleEntry tag
            self.rule_by_id: dict[str, Rule] = {}
            self.entry_to_ruleid: dict[str, str] = {}

            self.dynasty_keys = {
                name: f"{format_as_tag(name)}_DYNASTY" for name in self.dynasty_names
            }

        def _get_rules_dir(self):
            """Get the rules directory path for module 1."""
            return os.path.join(self.module_1_path, RULES_DIR)

        def _get_sub_rules_dir(self):
            """Get the substitution rules directory path for module 2."""
            return os.path.join(self.module_2_path, SUB_RULES_DIR)

        def _get_dynasties_path(self):
            """Get the dynasties file path for module 2."""
            return os.path.join(self.module_2_path, DYNASTIES_PATH)

        def _get_tag_names_path(self):
            """Get the tag names file path for module 2."""
            return os.path.join(self.module_2_path, TAG_NAMES_PATH)

        def _get_events_output_path(self):
            """Get the output path for the events file."""
            return build_event_file_path(self.event_name)

        def _get_localisation_output_path(self):
            """Get the output path for the localisation file."""
            return build_localisation_file_path(self.event_name)

        def _log_module(self, module: str, message: str):
            """Log a success message for a module."""
            log_module(module, message)

        def _log_product(self, message: str):
            """Log a success message for this product."""
            log_product(self.module_1, self.module_2, message)

        def _validate_required_data(self):
            """Validate that required data is loaded properly."""
            if not self.tag_name_list:
                self._log_product("WARNING: No tag names found")
            if not self.dynasty_names:
                self._log_product("WARNING: No dynasty names found")
            if not self.rules_list:
                self._log_product("WARNING: No rules found")

        def _has_duplicates_in_list(
            self, items: list, item_name: str = "items"
        ) -> bool:
            """Check if a list has duplicates and log warnings if found."""
            seen = set()
            duplicates = set()
            for item in items:
                if item in seen:
                    duplicates.add(item)
                else:
                    seen.add(item)

            if duplicates:
                self._log_product(
                    f"WARNING: Duplicate {item_name} found: {sorted(duplicates)}"
                )
                return True
            return False

        def _filter_rules_by_condition(
            self, rules: list[Rule], condition_func
        ) -> tuple[list[Rule], list[Rule]]:
            """Split rules into two lists based on a condition function."""
            matching = []
            non_matching = []
            for rule in rules:
                if condition_func(rule):
                    matching.append(rule)
                else:
                    non_matching.append(rule)
            return matching, non_matching

        def _build_rule_mappings(self):
            """Build helper mappings for efficient rule lookup."""
            for rule in self.rules_list + self.substitution_rules_list:
                self.rule_by_id[rule.id] = rule

        def _count_generated_items(self) -> dict[str, int]:
            """Count various generated items for reporting."""
            counts = {
                "rules": len(self.rules_list),
                "substitution_rules": len(self.substitution_rules_list),
                "global_rules": len(self.global_rules_list),
                "tagged_rules": len(self.tagged_rules_list),
                "tag_entries": sum(len(entries) for entries in self.rules.values()),
                "events": len(self.events),
                "dynasty_names": len(self.dynasty_names),
            }
            return counts

        def _add_localisation_entry(
            self, loc_lines: list, keys: list, key: str, name: str, name_adj: str
        ):
            """Add a localisation entry with both base and adjective forms."""
            loc_lines.append(f' {key}: "{name}"')
            loc_lines.append(f' {key}_ADJ: "{name_adj}"')
            keys.append(key)
            keys.append(f"{key}_ADJ")

        def _generate_conditions_for_entries(
            self, entries: list[RuleEntry]
        ) -> list[str]:
            """Generate condition blocks for a list of rule entries."""
            conditions = []
            for entry in entries:
                orig_rule_id = self.entry_to_ruleid.get(entry.tag)
                orig_rule = self.rule_by_id.get(orig_rule_id)
                dynasty_event_id = None
                if orig_rule and orig_rule.name_dynasty:
                    dynasty_event_id = self.events.get(orig_rule.id)

                conditions.append(
                    build_if_block(
                        limit=entry.condition,
                        override_name=entry.tag,
                        event_name=self.event_name,
                        event_id=dynasty_event_id,
                    )
                )
            return conditions

        def _create_event_for_tag(self, tag: str) -> str:
            """Create an event for a specific tag."""
            event_id = self.events[tag]
            conditions = self._generate_conditions_for_entries(self.rules[tag])
            return TAG_DEPENDANT_EVENT_TEMPLATE.format(
                event_name=self.event_name,
                id=event_id,
                tag=tag,
                conditions="\n".join(conditions),
            )

        def _create_event_for_substitution_rule(self, substitution_rule) -> str:
            """Create an event for a substitution rule."""
            event_id = self.events[substitution_rule.id]
            conditions = self._generate_conditions_for_entries(
                self.rules[substitution_rule.id]
            )
            return TAG_AGNOSTIC_EVENT_TEMPLATE.format(
                event_name=self.event_name,
                id=event_id,
                conditions="\n".join(conditions),
            )

        def assign_rules(self):
            """Assign generation rules for this product."""
            # Build rule_by_id map early so we can reference rules later
            for rule in self.rules_list:
                self.rule_by_id[rule.id] = rule

            # Map rules to applicable tags
            for rule in self.rules_list:
                if not rule.name:
                    continue
                if not any(x in rule.name for x in FORMAT_TEMPLATES) and not rule.tags:
                    self.global_rules_list.append(rule)
                else:
                    self.tagged_rules_list.append(rule)
                    target_tags = rule.tags or self.tag_name_list.keys()
                    for tag in target_tags:
                        self.tag_to_rules[tag].append(rule)

            # Build final rule entries per tag
            for tag, loc in self.tag_name_list.items():
                for rule in self.tag_to_rules[tag]:
                    name = get_country_name(rule.name, (tag, loc))
                    if not name:
                        continue

                    tag_name_value = get_tag_name(tag, rule.id)
                    name_adj = rule.name_adj or loc.adj

                    entry = RuleEntry(
                        tag=tag_name_value,
                        name=name,
                        name_adj=name_adj,
                        condition=rule.conditions,
                    )
                    self.rules[tag].append(entry)
                    # map the localisation tag back to the original rule id
                    self.entry_to_ruleid[entry.tag] = rule.id

            # Rules for substituting names
            for substitution_rule in self.substitution_rules_list:
                for rule in self.tagged_rules_list:
                    if set(substitution_rule.tags) & set(rule.tags) or rule.tags == []:
                        loc = Localisation(
                            substitution_rule.name,
                            substitution_rule.name_adj,
                        )
                        if not loc.adj:
                            raise RuntimeError(
                                "Substitution rule must have a defined adjective."
                            )
                        name = get_country_name(rule.name, (substitution_rule.id, loc))
                        if not name:
                            continue

                        tag_name_value = get_tag_name(substitution_rule.id, rule.id)
                        name_adj = rule.name_adj or loc.adj

                        entry = RuleEntry(
                            tag=tag_name_value,
                            name=name,
                            name_adj=name_adj,
                            condition=rule.conditions,
                        )

                        self.rules[substitution_rule.id].append(entry)
                        # map the localisation tag back to the original rule id
                        self.entry_to_ruleid[entry.tag] = rule.id

        def generate_event_script(self):
            """Generate the event script for this product."""
            # Compose event triggers for the initial event immediate block
            event_triggers = []

            # Assign event ids for tag-specific events and add triggers for them
            for tag in self.tag_name_list.keys():
                event_triggers.append(
                    build_if_block(
                        tag=tag,
                        event_name=self.event_name,
                        event_id=self.event_id,
                    )
                )
                self.events[tag] = str(self.event_id)
                self.event_id += 1

            # Assign event ids for substitution rules and add triggers for them
            for substitution_rule in self.substitution_rules_list:
                tags_str = ""
                if substitution_rule.tags != []:
                    tags_str = f"OR = {{ {' '.join(f'tag = {tag}' for tag in substitution_rule.tags)} }}"
                condition = substitution_rule.conditions or "always = yes"
                combined_limit = f"{tags_str} {condition}".strip()
                event_triggers.append(
                    build_if_block(
                        limit=combined_limit,
                        event_name=self.event_name,
                        event_id=self.event_id,
                    )
                )
                self.events[substitution_rule.id] = str(self.event_id)
                self.event_id += 1

            # Assign event ids for dynasty rules here but do not append them to the initial triggers
            dynasty_rules = [rule for rule in self.rules_list if rule.name_dynasty]
            for rule in dynasty_rules:
                self.events[rule.id] = str(self.event_id)
                self.event_id += 1

            # Add global rules directly to the initial triggers
            for rule in self.global_rules_list:
                event_triggers.append(
                    build_if_block(limit=rule.conditions, override_name=rule.id)
                )
                self.events[rule.id] = str(self.event_id)
                self.event_id += 1

            # Write event header with triggers
            event_lines = [
                EVENT_SCRIPT_HEADER.format(
                    event_name=self.event_name, event_triggers="\n".join(event_triggers)
                )
            ]

            # Country events per tag
            for tag in self.tag_name_list.keys():
                event_lines.append(self._create_event_for_tag(tag))

            # Country events per substituted name tag
            for substitution_rule in self.substitution_rules_list:
                event_lines.append(
                    self._create_event_for_substitution_rule(substitution_rule)
                )

            # Dynasty rules events
            for rule in dynasty_rules:
                id = self.events[rule.id]
                conditions = []
                for name in self.dynasty_names:
                    key = self.dynasty_keys[name]
                    limit_cond = f'dynasty = "{name}" NOT = {{ any_country = {{ dynasty = "{name}" }} }}'
                    conditions.append(
                        build_if_block(
                            limit=limit_cond, override_name=f"{key}_{rule.id}"
                        )
                    )
                event_lines.append(
                    TAG_AGNOSTIC_EVENT_TEMPLATE.format(
                        event_name=self.event_name,
                        id=id,
                        conditions="\n".join(conditions),
                    )
                )

            write_file_with_directory(
                self._get_events_output_path(), "\n".join(event_lines)
            )
            self._log_product("Writing event done")

        def generate_localisation(self):
            """Generate localisation lines and write to file.

            Returns the set of localisation keys generated for cross-file duplicate checking.
            """
            loc_lines = ["l_english:", "\n #tag rules\n"]
            keys = []
            for tag, entries in self.rules.items():
                loc_lines.append(f" # {tag}")
                for entry in entries:
                    self._add_localisation_entry(
                        loc_lines, keys, entry.tag, entry.name, entry.name_adj
                    )

            loc_lines.append(" #dynasties")
            for rule in self.rules_list:
                if rule.name_dynasty:
                    loc_lines.append(f"\n # {rule.id}")
                    for name in self.dynasty_names:
                        key = self.dynasty_keys[name]
                        dynasty_key = f"{key}_{rule.id}"
                        dynasty_name = rule.name_dynasty.replace(
                            "{DYNASTY}", name.title()
                        )
                        self._add_localisation_entry(
                            loc_lines, keys, dynasty_key, dynasty_name, name.title()
                        )

            # Only include global rules when module1 == module2 to avoid duplicates
            if self.module_1 == self.module_2:
                loc_lines.append(" #global rules")
                for rule in self.global_rules_list:
                    loc_lines.append(f"\n # {rule.id}")
                    self._add_localisation_entry(
                        loc_lines, keys, rule.id, rule.name, rule.name_adj
                    )

            ensure_directory(os.path.join(MOD_PATH, "localisation"))
            out_path = self._get_localisation_output_path()

            # Check duplicates within this localisation file (linear time)
            seen_local = set()
            dupes_local = set()
            for k in keys:
                if k in seen_local:
                    dupes_local.add(k)
                else:
                    seen_local.add(k)

            if dupes_local:
                uniq = sorted(dupes_local)
                self._log_product(
                    f"FAILURE: Duplicate localisation keys in product: {uniq}"
                )
                log_master("ABORTING")
                exit(1)

            write_file_with_directory(
                out_path, "\n".join(loc_lines), LOCALISATION_ENCODING
            )
            self._log_product(f"Writing localisation done: {out_path}")

            return set(keys)

        def build(self):
            """Build this product and return its generated keys."""
            self.assign_rules()
            self.generate_event_script()
            keys = self.generate_localisation()

            # Register keys with parent generator for duplicate checking
            self.generator._register_product_keys(self.event_name, keys)

            # Collect trigger for master dispatcher
            self.generator.triggers.append(
                f"country_event = {{ id = {self.event_name}.0 }}"
            )

            return keys

    def _log_duplicate_warning(self, key: str, event_name: str, other: str):
        """Log a duplicate key warning."""
        log_master(
            f"WARNING: Duplicate localisation key '{key}' generated by {event_name} and {other}"
        )

    def _report_statistics(self):
        """Report final generation statistics."""
        total_products = len(self.module_names) * len(self.module_names)
        total_unique_keys = len(self.generated_keys)
        duplicate_count = len(self.duplicate_keys)

        self._print_duplicate_summary(duplicate_count)
        self._print_final_stats(total_products, total_unique_keys, duplicate_count)

    def _print_duplicate_summary(self, duplicate_count: int):
        """Print detailed duplicate keys summary."""
        print_duplicate_keys_summary(self.duplicate_keys, duplicate_count)

    def _print_final_stats(
        self, total_products: int, total_unique_keys: int, duplicate_count: int
    ):
        """Print final generation statistics."""
        print_final_statistics(total_products, total_unique_keys, duplicate_count)

    def build_all(self):
        for module_1 in self.module_names:
            for module_2 in self.module_names:
                log_master(f"Building product: {module_1}_{module_2}")
                product = self.Product(self, module_1, module_2)
                product.build()  # Keys and triggers are automatically registered

        # write master event that dispatches to all products
        master_content = MASTER_EVENT_TEMPLATE.format(
            event_name=EVENT_NAME,
            module_triggers="\n".join("        " + t for t in self.triggers),
        )
        write_file_with_directory(
            build_master_event_file_path(EVENT_NAME), master_content
        )
        log_master("Writing dispatcher event done")

        # Generate duplicate keys report
        self._report_statistics()

    def generate_global_localisation(self):
        """Generate a global localisation file for decision keys that are shared across all products."""
        ensure_directory(os.path.join(MOD_PATH, "localisation"))

        global_loc_lines = [
            "#Generated by EU4 Dynamic Names Generator",
            "l_english:",
            " #decision",
            GLOBAL_DECISION_KEYS["title"],
            GLOBAL_DECISION_KEYS["desc"],
        ]

        global_loc_path = build_global_localisation_file_path(EVENT_NAME)
        write_file_with_directory(global_loc_path, "\n".join(global_loc_lines))
        log_master("Writing global localisation done")


def generate_on_actions():
    """Generate on_actions file that triggers events on various game events."""
    on_actions_lines = [
        f"{trigger} = {{ events = {{ {EVENT_NAME}.0 }} }}"
        for trigger in ON_ACTION_TRIGGERS
    ]

    on_actions_path = build_on_actions_file_path(EVENT_NAME)
    write_file_with_directory(on_actions_path, "\n\n".join(on_actions_lines))
    log_master("Writing on_actions done")


def generate_decision():
    """Generate decision file that allows manual triggering of name updates."""
    decision_content = DECISION_TEMPLATE.format(event_name=EVENT_NAME)
    decision_path = build_decisions_file_path(EVENT_NAME)
    write_file_with_directory(decision_path, decision_content)
    log_master("Writing decision done")


def build_modules(mods_root):
    """Main function to build all modules."""
    gen = Generator(mods_root)
    gen.build_all()
    gen.generate_global_localisation()
