#!/usr/bin/env python3

import os
from collections import defaultdict

from classes.RuleEntry import RuleEntry
from utils import *


class Product:
    """Manage a single localisation/product for a pair of modules.

    Responsibilities:
    - Load tag names, dynasties and rules for the two modules
    - Build rules -> RuleEntry mappings
    - Generate event script file for this product
    - Generate localisation file and return its keys for duplicate checking
    """

    def __init__(self, module_1: str, module_2: str):
        self.module_1 = module_1
        self.module_2 = module_2
        self.module_1_path = os.path.join(MODULES_ROOT, module_1)
        self.module_2_path = os.path.join(MODULES_ROOT, module_2)
        self.event_name = f"{EVENT_NAME}_{module_1.lower()}_{module_2.lower()}"

        self.rules_dir = os.path.join(self.module_1_path, RULES_DIR)
        self.sub_rules_dir = os.path.join(self.module_2_path, SUB_RULES_DIR)
        self.dynasties_path = os.path.join(self.module_2_path, DYNASTIES_PATH)
        self.tag_names_path = os.path.join(self.module_2_path, TAG_NAMES_PATH)

        # Load data
        self.tag_name_list = read_tag_names(self.tag_names_path)
        print(f"[{module_2}] Tag names read successfully")
        self.dynasty_names = read_lines(self.dynasties_path)
        print(f"[{module_2}] Dynasty names read successfully")
        self.rules_list: list[Rule] = parse_rules_dir(self.rules_dir)
        print(f"[{module_1}] Rules read successfully")
        self.substitution_rules_list: list[Rule] = parse_rules_dir(self.sub_rules_dir)
        print(f"[{module_2}] Substitution rules read successfully")

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

    def assign_rules(self):
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
            id = self.events[tag]
            conditions = []
            for entry in self.rules[tag]:
                # find the original rule for this entry so we can check for dynasty linkage
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
            event_lines.append(
                TAG_DEPENDANT_EVENT_TEMPLATE.format(
                    event_name=self.event_name,
                    id=id,
                    tag=tag,
                    conditions="\n".join(conditions),
                )
            )

        # Country events per substituted name tag
        for substitution_rule in self.substitution_rules_list:
            id = self.events[substitution_rule.id]
            conditions = []
            for entry in self.rules[substitution_rule.id]:
                # find the original rule for this entry so we can check for dynasty linkage
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
            event_lines.append(
                TAG_AGNOSTIC_EVENT_TEMPLATE.format(
                    event_name=self.event_name,
                    id=id,
                    conditions="\n".join(conditions),
                )
            )

        # Dynasty rules events
        for rule in dynasty_rules:
            id = self.events[rule.id]
            conditions = []
            for name in self.dynasty_names:
                key = self.dynasty_keys[name]
                limit_cond = f'dynasty = "{name}" NOT = {{ any_country = {{ dynasty = "{name}" }} }}'
                conditions.append(
                    build_if_block(limit=limit_cond, override_name=f"{key}_{rule.id}")
                )
            event_lines.append(
                TAG_AGNOSTIC_EVENT_TEMPLATE.format(
                    event_name=self.event_name, id=id, conditions="\n".join(conditions)
                )
            )

        os.makedirs(f"{MOD_PATH}/events", exist_ok=True)
        with open(f"{MOD_PATH}/events/{self.event_name}_events.txt", "w+") as f:
            f.write("\n".join(event_lines))

        print(f"[{self.module_1}_{self.module_2}] Writing event done")

    def generate_localisation(self):
        """Generate localisation lines and write to file.

        Returns the set of localisation keys generated for cross-file duplicate checking.
        """
        loc_lines = ["l_english:", "\n #tag rules\n"]
        keys = []
        for tag, entries in self.rules.items():
            loc_lines.append(f" # {tag}")
            for entry in entries:
                loc_lines.append(f' {entry.tag}: "{entry.name}"')
                loc_lines.append(f' {entry.tag}_ADJ: "{entry.name_adj}"')
                keys.append(entry.tag)
                keys.append(f"{entry.tag}_ADJ")

        loc_lines.append(" #dynasties")
        for rule in self.rules_list:
            if rule.name_dynasty:
                loc_lines.append(f"\n # {rule.id}")
                for name in self.dynasty_names:
                    key = self.dynasty_keys[name]
                    loc_lines.append(
                        f' {key}_{rule.id}: "{rule.name_dynasty.replace("{DYNASTY}", name.title())}"'
                    )
                    loc_lines.append(f' {key}_{rule.id}_ADJ: "{name.title()}"')
                    keys.append(f"{key}_{rule.id}")
                    keys.append(f"{key}_{rule.id}_ADJ")

        # Only include global rules when module1 == module2 to avoid duplicates
        if self.module_1 == self.module_2:
            loc_lines.append(" #global rules")
            for rule in self.global_rules_list:
                loc_lines.append(f"\n # {rule.id}")
                loc_lines.append(f' {rule.id}: "{rule.name}"')
                loc_lines.append(f' {rule.id}_ADJ: "{rule.name_adj}"')
                keys.append(rule.id)
                keys.append(f"{rule.id}_ADJ")

        os.makedirs(f"{MOD_PATH}/localisation", exist_ok=True)
        out_path = (
            f"{MOD_PATH}/localisation/{self.event_name}_localisation_l_english.yml"
        )
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
            print(
                f"[{self.module_1}_{self.module_2}] FAILURE: Duplicate localisation keys in product: {uniq}"
            )
            print("[master] ABORTING")
            exit(1)

        with open(out_path, "w+", encoding="utf-8-sig") as f:
            f.write("\n".join(loc_lines))

        print(
            f"[{self.module_1}_{self.module_2}] Writing localisation done: {out_path}"
        )

        return set(keys)

    def build(self):
        self.assign_rules()
        self.generate_event_script()
        return self.generate_localisation()


class Generator:
    """Top-level generator that iterates over modules and builds Product instances.

    Responsibilities:
    - Iterate all module pairs in modules_root
    - Create Product(module_1, module_2), build it and collect its localisation keys
    - Write a master dispatcher event file that references all per-product events
    - Fail if any localisation key is generated more than once across products
    """

    def __init__(self, modules_root: str):
        self.modules_root = modules_root
        self.module_names = sorted(os.listdir(modules_root))
        self.generated_keys: dict[str, str] = {}  # key -> product event_name
        self.duplicate_keys: dict[str, list[str]] = (
            {}
        )  # key -> list of products that generated it
        self.triggers: list[str] = []

    def build_all(self):
        for module_1 in self.module_names:
            for module_2 in self.module_names:
                print(f"[master] Building product: {module_1}_{module_2}")
                product = Product(module_1, module_2)
                keys = product.build()

                # collect triggers for master dispatcher
                event_name = f"{EVENT_NAME}_{module_1.lower()}_{module_2.lower()}"
                self.triggers.append(f"country_event = {{ id = {event_name}.0 }}")

                # collect duplicates across generated localisation keys
                for k in keys:
                    if k in self.generated_keys:
                        other = self.generated_keys[k]
                        print(
                            f"[master] WARNING: Duplicate localisation key '{k}' generated by {event_name} and {other}"
                        )

                        # Track all products that generate this key
                        if k not in self.duplicate_keys:
                            self.duplicate_keys[k] = [other]
                        self.duplicate_keys[k].append(event_name)
                    else:
                        self.generated_keys[k] = event_name

        # write master event that dispatches to all products
        os.makedirs(f"{MOD_PATH}/events", exist_ok=True)
        with open(f"{MOD_PATH}/events/{EVENT_NAME}_master_events.txt", "w+") as f:
            f.write(
                MASTER_EVENT_TEMPLATE.format(
                    event_name=EVENT_NAME,
                    module_triggers="\n".join("        " + t for t in self.triggers),
                )
            )

        print("[master] Writing dispatcher event done")

        # Generate duplicate keys report
        if self.duplicate_keys:
            print(
                f"\n[master] DUPLICATE KEYS SUMMARY: Found {len(self.duplicate_keys)} duplicate localisation keys:"
            )
            print("=" * 80)
            for key, products in sorted(self.duplicate_keys.items()):
                print(f"\nKey: {key}")
                print(f"Generated by: {', '.join(products)}")
            print("=" * 80)
            print(
                f"[master] Total products built: {len(self.module_names) * len(self.module_names)}"
            )
            print(f"[master] Total unique keys: {len(self.generated_keys)}")
            print(f"[master] Duplicate keys: {len(self.duplicate_keys)}")
        else:
            print(f"\n[master] SUCCESS: No duplicate localisation keys found!")
            print(
                f"[master] Total products built: {len(self.module_names) * len(self.module_names)}"
            )
            print(f"[master] Total unique keys: {len(self.generated_keys)}")

    def generate_global_localisation(self):
        """Generate a global localisation file for decision keys that are shared across all products."""
        os.makedirs(f"{MOD_PATH}/localisation", exist_ok=True)

        global_loc_lines = [
            "#Generated by EU4 Dynamic Names Generator",
            "l_english:",
            " #decision",
            'update_dynamic_names_decision_title: "Update Dynamic Names"',
            'update_dynamic_names_decision_desc: "Force update dynamic names (e.g. after a government rank change). Happens automatically every 2 in-game years."',
        ]

        with open(
            f"{MOD_PATH}/localisation/{EVENT_NAME}_global_localisation_l_english.yml",
            "w+",
        ) as f:
            f.write("\n".join(global_loc_lines))

        print(f"[master] Writing global localisation done")


def generate_on_actions():
    triggers = [
        "on_bi_yearly_pulse",
        "on_country_creation",
        "on_country_released",
        "on_government_change",
        "on_monarch_death",
        "on_native_change_government",
        "on_primary_culture_changed",
        "on_reform_changed",
        "on_reform_enacted",
        "on_religion_change",
        "on_startup",
    ]

    on_actions_lines = [
        f"{trigger} = {{ events = {{ {EVENT_NAME}.0 }} }}" for trigger in triggers
    ]

    os.makedirs(f"{MOD_PATH}/common/on_actions", exist_ok=True)
    with open(f"{MOD_PATH}/common/on_actions/{EVENT_NAME}_on_actions.txt", "w+") as f:
        f.write("\n\n".join(on_actions_lines))

    print(f"[master] Writing on_actions done")


def generate_decision():
    os.makedirs(f"{MOD_PATH}/decisions", exist_ok=True)
    with open(f"{MOD_PATH}/decisions/{EVENT_NAME}_decisions.txt", "w+") as f:
        f.write(DECISION_TEMPLATE.format(event_name=EVENT_NAME))

    print(f"[master] Writing decision done")


def build_modules(mods_root):
    gen = Generator(mods_root)
    gen.build_all()
    gen.generate_global_localisation()


if __name__ == "__main__":
    build_modules(MODULES_ROOT)
    generate_on_actions()
    generate_decision()
