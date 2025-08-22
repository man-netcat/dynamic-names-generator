import os
import pyradox

from classes.Localisation import Localisation
from classes.Rule import Rule
from defines.defines import *

# -----------------
# Utility Functions
# -----------------


def process_name(name: str) -> str:
    return name.replace('"', "").replace("\n", "").strip()


def get_tag_name(tag: str, tag_name: str) -> str:
    return f"{tag}_{tag_name}"


def format_as_tag(s: str) -> str:
    return s.upper().replace(" ", "_").replace("-", "_").replace("'", "_")


def split_stripped(s: str, sep: str = ",", maxsplit: int = -1) -> list[str]:
    return [part.strip() for part in s.split(sep, maxsplit)]


def build_conditions(tree) -> str:
    return " ".join(map(str.strip, str(tree).split("\n"))).strip()


def build_tags(tree) -> list[str]:
    return list(tree["tags"].values()) if tree and "tags" in tree else []


def build_if_block(
    limit: str = None, tag: str = None, event_id: int = None, override_name: str = None
) -> str:
    if not (event_id or override_name):
        raise RuntimeError("event_id or override_name must be specified")

    conditions = []
    if tag:
        conditions.append(f"tag = {tag}")
    if limit:
        conditions.append(limit)

    limit_str = " ".join(conditions) if conditions else "always = yes"

    actions = []
    if override_name:
        actions.append(f"override_country_name = {override_name}")
    if event_id:
        actions.append(f"country_event = {{ id = {EVENT_NAME}.{event_id} }}")

    actions_str = " ".join(actions)

    return f"        if = {{ limit = {{ {limit_str} }} {actions_str} }}"


def read_rule_file(path: str):
    return pyradox.txt.parse_file(path=path, game="EU4", path_relative_to_game=False)


def substitute(template: str, format_str: str, item_name: str) -> str:
    return template.replace(format_str, item_name)


def read_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8-sig") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def get_country_name(rule_name: str, tag_name: tuple[str, Localisation]) -> str:
    if "NAME_ADJ" in rule_name:
        return substitute(rule_name, "{NAME_ADJ}", tag_name[1].adj)
    elif "NAME" in rule_name:
        return substitute(rule_name, "{NAME}", tag_name[1].name)
    elif "DYNASTY" in rule_name:
        return None
    return rule_name


def get_dynasty_name(rule_name: str, dynasty_name: str) -> str:
    if "DYNASTY" in rule_name:
        return substitute(rule_name, "{DYNASTY}", dynasty_name.capitalize())
    return None


def get_item_name(rule_name: str, item_name: str) -> str:
    return substitute(rule_name, "{ITEM_NAME}", item_name)


# ------------------------------------
# Extraction / Rule-Building Functions
# ------------------------------------


def parse_rule_data(
    key: str, rule_data: dict, parent_tags=None, parent_conditions=""
) -> list[Rule]:
    """Recursively parse rule data (grouped or regular)."""
    if parent_tags is None:
        parent_tags = []

    rules: list[Rule] = []

    group_tags = parent_tags + build_tags(rule_data)
    group_conditions = parent_conditions
    if "conditions" in rule_data:
        if parent_conditions:
            group_conditions = (
                f"{parent_conditions} {build_conditions(rule_data['conditions'])}"
            )
        else:
            group_conditions = build_conditions(rule_data["conditions"])

    # Handle grouped rules
    if "group" in rule_data:
        group_name_template = rule_data["name"] if "name" in rule_data else None
        for sub_key in rule_data["group"]:
            sub_rule = rule_data["group"][sub_key]
            if group_name_template and "name" in sub_rule:
                sub_rule["name"] = get_item_name(group_name_template, sub_rule["name"])
            rules.extend(
                parse_rule_data(
                    get_tag_name(key, sub_key), sub_rule, group_tags, group_conditions
                )
            )
        return rules

    # Handle regular rule
    rule_name = rule_data["name"] if "name" in rule_data else None
    name_adj = rule_data["name_adj"] if "name_adj" in rule_data else None
    name_dynasty = rule_data["name_dynasty"] if "name_dynasty" in rule_data else None

    rules.append(
        Rule(
            id=key,
            name=rule_name,
            name_adj=name_adj,
            name_dynasty=name_dynasty,
            tags=group_tags,
            conditions=group_conditions,
        )
    )
    return rules


def parse_rule_file(file_path: str) -> list[Rule]:
    data = read_rule_file(file_path)
    all_rules: list[Rule] = []

    for key in data:
        all_rules.extend(parse_rule_data(key, data[key]))

    return all_rules


def parse_rules_dir(dir_path: str) -> list[Rule]:
    all_rules: list[Rule] = []

    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        if os.path.isfile(file_path):
            all_rules.extend(parse_rule_file(file_path))

    return all_rules


def read_tag_names(file_path: str) -> dict[str, Localisation]:
    tag_name_list: dict[str, Localisation] = {}

    for line in read_lines(file_path):
        name, value = line.split(":", 1)
        if "_ADJ2" in name:
            continue
        value = process_name(value)
        if "_ADJ" in name:
            key = name.replace("_ADJ", "")
            tagName = tag_name_list[key]
            tagName.adj = value
        else:
            tag_name_list[name] = Localisation(name=value, adj=None)
    return tag_name_list
