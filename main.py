#!/usr/bin/env python3

from utils import *
from classes.rule_entry import RuleEntry
import os
from collections import defaultdict


class ModBuilder:
    def __init__(self):
        # Read rules, tag names, and dynasty names from input files
        self.rules_list = read_rules()
        print("Rules read successfully")
        self.tag_name_list = read_tag_names()
        print("Tag names read successfully")
        self.dynasty_names = read_dynasties()
        print("Dynasty names read successfully")

        # Prepare lists and dictionaries for processing
        self.tag_names = list(self.tag_name_list.items())
        self.rules: dict[str, list[RuleEntry]] = defaultdict(list)
        self.tag_to_rules: dict[str, list[RuleEntry]] = defaultdict(list)
        self.events = {}
        self.event_id = 1
        # Generate keys for dynasty names for localisation/events
        self.dynasty_keys = {
            name: name.upper().replace(" ", "_").replace("-", "_").replace("'", "")
            for name in self.dynasty_names
        }

    # Assign rules to tags based on their conditions
    def assign_rules_to_tags(self):
        for rule in self.rules_list:
            if not rule.tags:
                # If rule has no tags, assign to all tags
                for tag, _ in self.tag_names:
                    self.tag_to_rules[tag].append(rule)
            else:
                # Otherwise, assign to specified tags
                for tag in rule.tags:
                    self.tag_to_rules[tag].append(rule)

        # For each tag, process rules and generate RuleEntry objects
        for tag, _ in self.tag_names:
            for rule in self.tag_to_rules[tag]:
                name = get_country_name(rule.name, (tag, self.tag_name_list[tag]))
                if name:
                    tag_name_value = get_tag_name(tag, rule.tag_name)
                    # Special case for Teutonic Order Electorate
                    if tag_name_value == "TEO_ELECTORATE":
                        tag_name_value = "TEO_ELECTORATE_NAME"
                    self.rules[tag].append(
                        RuleEntry(tag_name_value, name, " ".join(rule.conditions))
                    )

    # Generate event script for dynamic country names
    def generate_event_script(self):
        # Collect rules that use dynasty names
        dynasty_rules = [
            (rule.name, " ".join(rule.conditions), rule.tag_name)
            for rule in self.rules_list
            if "{DYNASTY}" in rule.name
        ]

        # Start building event script lines
        event_lines = [
            "### generated events for dynamic names\n",
            f"namespace = {EVENT_NAME}\n\n",
            "country_event = {",
            f"\tid = {EVENT_NAME}.0",
            f"\ttitle = {EVENT_NAME}.0.title",
            f"\tdesc = {EVENT_NAME}.0.desc",
            "\tpicture = TRADEGOODS_eventPicture\n",
            "\thidden = yes",
            "\tis_triggered_only = yes\n",
            "\timmediate = {",
        ]

        # Add event triggers for each tag
        for tag, _ in self.tag_names:
            event_lines.append(
                f"\t\tif = {{ limit = {{ tag = {tag} }} country_event = {{ id = {EVENT_NAME}.{self.event_id} }} }}"
            )
            self.events[tag] = str(self.event_id)
            self.event_id += 1

        # Add event triggers for dynasty rules
        for rule in dynasty_rules:
            event_lines.append(
                f"\t\tif = {{ limit = {{ {rule[1]} }} country_event = {{ id = {EVENT_NAME}.{self.event_id} }} }}"
            )
            self.events[rule[0]] = str(self.event_id)
            self.event_id += 1

        event_lines += [
            "\t}",
            "\toption = {",
            f"\t\tname = {EVENT_NAME}.0.a",
            "\t}",
            "}",
        ]

        # Generate country events for each tag
        for tag, _ in self.tag_names:
            id = self.events[tag]
            tag_event = [
                "country_event = {",
                f"\tid = {EVENT_NAME}.{id}",
                f"\ttitle = {EVENT_NAME}.{id}.title",
                f"\tdesc = {EVENT_NAME}.{id}.desc",
                "\tpicture = TRADEGOODS_eventPicture\n",
                "\thidden = yes",
                "\tis_triggered_only = yes\n",
                f"\ttrigger = {{ tag = {tag} }}\n",
                "\timmediate = {",
            ]
            for rule in self.rules[tag]:
                tag_event.append(
                    f"\t\tif = {{ limit = {{ {rule.condition} }} override_country_name = {rule.tag} }}"
                )
            tag_event += [
                "\t}",
                "\toption = {",
                f"\t\tname = {EVENT_NAME}.{id}.a",
                "\t}",
                "}",
            ]
            event_lines.extend(tag_event)

        # Generate country events for dynasty rules
        for rule in dynasty_rules:
            id = self.events[rule[0]]
            dynasty_event = [
                "country_event = {",
                f"\tid = {EVENT_NAME}.{id}",
                f"\ttitle = {EVENT_NAME}.{id}.title",
                f"\tdesc = {EVENT_NAME}.{id}.desc",
                "\tpicture = TRADEGOODS_eventPicture\n",
                "\thidden = yes",
                "\tis_triggered_only = yes\n",
                "\timmediate = {",
            ]
            for name in self.dynasty_names:
                key = self.dynasty_keys[name]
                dynasty_event.append(
                    f'\t\tif = {{ limit = {{ dynasty = "{name}" }} override_country_name = {key}_{rule[2]} }}'
                )
            dynasty_event += [
                "\t}",
                "\toption = {",
                f"\t\tname = {EVENT_NAME}.{id}.a",
                "\t}",
                "}",
            ]
            event_lines.extend(dynasty_event)

        # Write event script to file
        os.makedirs("../events", exist_ok=True)
        with open(f"../events/{EVENT_NAME}_events.txt", "w+") as f:
            f.write("\n".join(event_lines))

        print("Writing event done")

    # Generate localisation file for country names and dynasties
    def generate_localisation(self):
        loc_lines = ["l_english:", "\n #tag rules\n"]
        for tag, entries in self.rules.items():
            loc_lines.append(f" # {tag}")
            for entry in entries:
                loc_lines.append(f' {entry.tag}: "{entry.name}"')
                loc_lines.append(f' {entry.tag}_ADJ: "{self.tag_name_list[tag].adj}"')
                if self.tag_name_list[tag].adj2:
                    loc_lines.append(
                        f' {entry.tag}_ADJ2: "{self.tag_name_list[tag].adj2}"'
                    )

        loc_lines.append(" #dynasties")
        for rule in self.rules_list:
            if "{DYNASTY}" in rule.name:
                loc_lines.append(f"\n # {rule.tag_name}")
                for name in self.dynasty_names:
                    key = self.dynasty_keys[name]
                    loc_lines.append(
                        f" {key}_{rule.tag_name}: \"{rule.name.replace('{DYNASTY}', name.title())}\""
                    )
                    loc_lines.append(f' {key}_{rule.tag_name}_ADJ: "{name.title()}"')

        # Add localisation for decision
        loc_lines.append('update_dynamic_names_decision_title: "Update Dynamic Names"')
        loc_lines.append(
            'update_dynamic_names_decision_desc: "Force update dynamic names (e.g. after a government rank change). Happens automatically every 2 in-game years."'
        )

        # Write localisation to file
        os.makedirs("../localisation", exist_ok=True)
        with open(
            f"../localisation/{EVENT_NAME}_localisation_l_english.yml",
            "w+",
            encoding="utf-8-sig",
        ) as f:
            f.write("\n".join(loc_lines))

        print("Writing localisation done")

    # Generate on_actions file to trigger events on game actions
    def generate_on_actions(self):
        on_actions_lines = [
            "on_startup = { events = { %s.0 } }" % EVENT_NAME,
            "on_government_change = { events = { %s.0 } }" % EVENT_NAME,
            "on_native_change_government = { events = { %s.0 } }" % EVENT_NAME,
            "on_religion_change = { events = { %s.0 } }" % EVENT_NAME,
            "on_primary_culture_changed = { events = { %s.0 } }" % EVENT_NAME,
            "on_monarch_death = { events = { %s.0 } }" % EVENT_NAME,
            "on_country_creation = { events = { %s.0 } }" % EVENT_NAME,
            "on_bi_yearly_pulse = { events = { %s.0 } }" % EVENT_NAME,
            "on_country_released = { events = { %s.0 } }" % EVENT_NAME,
        ]

        # Write on_actions to file
        os.makedirs("../common/on_actions", exist_ok=True)
        with open(f"../common/on_actions/{EVENT_NAME}_on_actions.txt", "w+") as f:
            f.write("\n\n".join(on_actions_lines))

        print("Writing on_actions done")

    # Generate decision file for updating dynamic names
    def generate_decision(self):
        decision_lines = [
            "country_decisions = {",
            "\tupdate_dynamic_names_decision = {",
            "\t\tpotential = { always = yes }",
            "\t\tallow = { always = yes }",
            "\t\tai_will_do = { factor = 0 }",
            f"\t\teffect = {{ country_event = {{ id = {EVENT_NAME}.0 }} }}",
            "\t}",
            "}",
        ]

        # Write decision to file
        os.makedirs("../decisions", exist_ok=True)
        with open(f"../decisions/{EVENT_NAME}_decisions.txt", "w+") as f:
            f.write("\n".join(decision_lines))

        print("Writing decision done")

    # Main build function to run all generation steps
    def build(self):
        self.assign_rules_to_tags()
        self.generate_event_script()
        self.generate_localisation()
        self.generate_on_actions()
        self.generate_decision()


# Entry point for script execution
if __name__ == "__main__":
    builder = ModBuilder()
    builder.build()
