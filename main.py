from utils import *
from classes.rule_entry import RuleEntry
import os
from collections import defaultdict

if __name__ == "__main__":
    rules_list = read_rules()
    print("Rules read successfully")
    tag_name_list = read_tag_names()
    tag_names = list(tag_name_list.items())
    print("Tag names read successfully")
    dynasty_names = read_dynasties()
    print("Dynasty names read successfully")

    rules: dict[str, list[RuleEntry]] = defaultdict(list)
    tag_to_rules: dict[str, list[RuleEntry]] = defaultdict(list)

    for rule in rules_list:
        if not rule.tags:
            for tag, _ in tag_names:
                tag_to_rules[tag].append(rule)
        else:
            for tag in rule.tags:
                tag_to_rules[tag].append(rule)

    for tag, _ in tag_names:
        for rule in tag_to_rules[tag]:
            name = get_country_name(rule.name, (tag, tag_name_list[tag]))
            if name:
                tag_name_value = get_tag_name(tag, rule.tag_name)
                if tag_name_value == "TEO_ELECTORATE":
                    tag_name_value = "TEO_ELECTORATE_NAME"
                rules[tag].append(
                    RuleEntry(tag_name_value, name, " ".join(rule.conditions))
                )

    dynasty_rules = [
        (rule.name, " ".join(rule.conditions), rule.tag_name)
        for rule in rules_list
        if "{DYNASTY}" in rule.name
    ]

    dynasty_keys = {
        name: name.upper().replace(" ", "_").replace("-", "_").replace("'", "")
        for name in dynasty_names
    }

    event_lines = [
        "### generated events for dynamic names\n",
        f"namespace = {EVENT_NAME}\n\n",
    ]

    event_lines += [
        "country_event = {",
        f"\tid = {EVENT_NAME}.0",
        f"\ttitle = {EVENT_NAME}.0.title",
        f"\tdesc = {EVENT_NAME}.0.desc",
        "\tpicture = TRADEGOODS_eventPicture\n",
        "\thidden = yes",
        "\tis_triggered_only = yes\n",
        "\timmediate = {",
    ]

    events = {}
    event_id = 1
    for tag, _ in tag_names:
        event_lines.append(
            f"\t\tif = {{ limit = {{ tag = {tag} }} country_event = {{ id = {EVENT_NAME}.{event_id} }} }}"
        )
        events[tag] = str(event_id)
        event_id += 1

    for rule in dynasty_rules:
        event_lines.append(
            f"\t\tif = {{ limit = {{ {rule[1]} }} country_event = {{ id = {EVENT_NAME}.{event_id} }} }}"
        )
        events[rule[0]] = str(event_id)
        event_id += 1

    event_lines += ["\t}", "\toption = {", f"\t\tname = {EVENT_NAME}.0.a", "\t}", "}"]

    for tag, _ in tag_names:
        id = events[tag]
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
        for rule in rules[tag]:
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

    for rule in dynasty_rules:
        id = events[rule[0]]
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
        for name in dynasty_names:
            key = dynasty_keys[name]
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

    os.makedirs("../events", exist_ok=True)
    with open(f"../events/{EVENT_NAME}_events.txt", "w+") as f:
        f.write("\n".join(event_lines))

    print("\nWriting event done")

    loc_lines = ["l_english:", "\n #tag rules\n"]
    for tag, entries in rules.items():
        loc_lines.append(f" # {tag}")
        for entry in entries:
            loc_lines.append(f' {entry.tag}: "{entry.name}"')
            loc_lines.append(f' {entry.tag}_ADJ: "{tag_name_list[tag].adj}"')
            if tag_name_list[tag].adj2:
                loc_lines.append(f' {entry.tag}_ADJ2: "{tag_name_list[tag].adj2}"')

    loc_lines.append(" #dynasties")
    for rule in dynasty_rules:
        loc_lines.append(f"\n # {rule[2]}")
        for name in dynasty_names:
            key = dynasty_keys[name]
            loc_lines.append(
                f" {key}_{rule[2]}: \"{rule[0].replace('{DYNASTY}', name.title())}\""
            )
            loc_lines.append(f' {key}_{rule[2]}_ADJ: "{name.title()}"')

    loc_lines.append('update_dynamic_names_decision_title: "Update Dynamic Names"')
    loc_lines.append(
        'update_dynamic_names_decision_desc: "Force update dynamic names (e.g. after a government rank change). Happens automatically every 2 in-game years."'
    )

    os.makedirs("../localisation", exist_ok=True)
    with open(
        f"../localisation/{EVENT_NAME}_localisation_l_english.yml",
        "w+",
        encoding="utf-8-sig",
    ) as f:
        f.write("\n".join(loc_lines))

    print("\nWriting localisation done")

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

    os.makedirs("../common/on_actions", exist_ok=True)
    with open(f"../common/on_actions/{EVENT_NAME}_on_actions.txt", "w+") as f:
        f.write("\n\n".join(on_actions_lines))

    print("Writing on_actions done")

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

    os.makedirs("../decisions", exist_ok=True)
    with open(f"../decisions/{EVENT_NAME}_decisions.txt", "w+") as f:
        f.write("\n".join(decision_lines))

    print("Writing decision done")
