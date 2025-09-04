#!/usr/bin/env python3

import os
from collections import defaultdict

from classes.RuleEntry import RuleEntry
from utils import *


class Generator:
    def __init__(self, module_name):
        self.module_name = module_name
        self.module_path = os.path.join(MODULES_ROOT, module_name)
        self.event_name = f"{EVENT_NAME}_{module_name.lower()}"

        # Paths inside this mod, fallback to vanilla if missing
        def path_or_vanilla(relative_path):
            mod_file = os.path.join(self.module_path, relative_path)
            if os.path.exists(mod_file):
                return mod_file
            return os.path.join(MODULES_ROOT, "00_vanilla", relative_path)

        self.rules_dir = path_or_vanilla(RULES_DIR)
        self.sub_rules_dir = path_or_vanilla(SUB_RULES_DIR)
        self.dynasties_path = path_or_vanilla(DYNASTIES_PATH)
        self.tag_names_path = path_or_vanilla(TAG_NAMES_PATH)

        # Load data
        self.tag_name_list = read_tag_names(self.tag_names_path)
        print(f"[{module_name}] Tag names read successfully")
        self.dynasty_names = read_lines(self.dynasties_path)
        print(f"[{module_name}] Dynasty names read successfully")
        self.rules_list: list[Rule] = parse_rules_dir(self.rules_dir)
        print(f"[{module_name}] Rules read successfully")
        self.substitution_rules_list: list[Rule] = parse_rules_dir(self.sub_rules_dir)
        print(f"[{module_name}] Substitution rules read successfully")

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

        print(f"[{self.module_name}] Writing event done")

    def generate_localisation(self):
        loc_lines = ["l_english:", "\n #tag rules\n"]
        for tag, entries in self.rules.items():
            loc_lines.append(f" # {tag}")
            for entry in entries:
                loc_lines.append(f' {entry.tag}: "{entry.name}"')
                loc_lines.append(f' {entry.tag}_ADJ: "{entry.name_adj}"')

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

        loc_lines.append(" #global rules")
        for rule in self.global_rules_list:
            loc_lines.append(f"\n # {rule.id}")
            loc_lines.append(f' {rule.id}: "{rule.name}"')
            loc_lines.append(f' {rule.id}_ADJ: "{rule.name_adj}"')

        loc_lines.append(" #decision")
        loc_lines.append('update_dynamic_names_decision_title: "Update Dynamic Names"')
        loc_lines.append(
            'update_dynamic_names_decision_desc: "Force update dynamic names (e.g. after a government rank change). Happens automatically every 2 in-game years."'
        )

        os.makedirs(f"{MOD_PATH}/localisation", exist_ok=True)
        with open(
            f"{MOD_PATH}/localisation/{self.event_name}_localisation_l_english.yml",
            "w+",
            encoding="utf-8-sig",
        ) as f:
            f.write("\n".join(loc_lines))

        print(f"[{self.module_name}] Writing localisation done")

        # Check for duplicates
        seen = set()
        duplicates = []

        for line in loc_lines:
            if line.strip().startswith("#"):
                continue
            if ":" in line:
                key = line.split(":", 1)[0].strip()
                if key in seen:
                    duplicates.append(key)
                else:
                    seen.add(key)

        if duplicates:
            print(f"[{self.module_name}] FAILURE: Duplicate localisation keys found:")
            for key in duplicates:
                print(" -", key)
            print(f"[{self.module_name}] ABORTING")
            exit(1)

    def build(self):
        self.assign_rules()
        self.generate_event_script()
        self.generate_localisation()


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
    mod_names = sorted(os.listdir(mods_root))
    triggers = []

    for mod_name in mod_names:
        mod_base_dir = os.path.join(mods_root, mod_name)
        if not os.path.isdir(mod_base_dir):
            continue
        print(f"[master] Building mod: {mod_name}")
        builder = Generator(mod_name)
        builder.build()

        event_name = f"{EVENT_NAME}_{mod_name.lower()}"
        triggers.append(f"country_event = {{ id = {event_name}.0 }}")

    os.makedirs(f"{MOD_PATH}/events", exist_ok=True)
    with open(f"{MOD_PATH}/events/{EVENT_NAME}_master_events.txt", "w+") as f:
        f.write(
            MASTER_EVENT_TEMPLATE.format(
                event_name=EVENT_NAME,
                module_triggers="\n".join("        " + t for t in triggers),
            )
        )

    print("[master] Writing dispatcher event done")


if __name__ == "__main__":
    build_modules(MODULES_ROOT)
    generate_on_actions()
    generate_decision()
