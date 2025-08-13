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
    return tag + "_" + tag_name


def format_as_tag(str: str):
    return str.upper().replace(" ", "_").replace("-", "_").replace("'", "")


def split_stripped(s: str, sep: str = ",", maxsplit: int = -1) -> list[str]:
    return [part.strip() for part in s.split(sep, maxsplit)]


def build_conditions(tree) -> str:
    return " ".join(map(str.strip, str(tree).split("\n")))


def read_rule_file(path: str):
    return pyradox.txt.parse_file(
        path=path,
        game="EU4",
        path_relative_to_game=False,
    )


def read_lines(path: str):
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            yield line


def get_country_name(rule_name: str, tag_name: tuple[str, Localisation]) -> str:
    if "NAME_ADJ2" in rule_name:
        rule_name = rule_name.replace("{NAME_ADJ2}", tag_name[1].adj2)
    elif "NAME_ADJ" in rule_name:
        rule_name = rule_name.replace("{NAME_ADJ}", tag_name[1].adj)
    elif "NAME" in rule_name:
        rule_name = rule_name.replace("{NAME}", tag_name[1].name)
    elif "DYNASTY" not in rule_name:
        rule_name = rule_name
    else:
        rule_name = None
    return rule_name


def get_dynasty_name(rule_name: str, dynasty_name: str) -> str:
    if "DYNASTY" in rule_name:
        rule_name = rule_name.replace("{DYNASTY}", dynasty_name.capitalize())
    else:
        rule_name = None
    return rule_name


# ------------------------------------
# Extraction / Rule-Building Functions
# ------------------------------------


def parse_rule(
    key: str,
    rule_data: dict,
    group_tags: list[str] = [],
    group_conditions: str = None,
) -> Rule:
    group_tags = group_tags or []
    combined_conditions = []
    if group_conditions:
        combined_conditions.append(group_conditions)
    if "conditions" in rule_data:
        combined_conditions.append(build_conditions(rule_data["conditions"]))

    tags = group_tags + (
        list(rule_data["tags"].values()) if "tags" in rule_data else []
    )

    return Rule(
        id=key,
        name=rule_data["name"],
        name_adj=rule_data["name_adj"],
        tags=tags,
        conditions=combined_conditions,
    )


def read_rules(path: str) -> list[Rule]:
    data = read_rule_file(path)
    rules = [parse_rule(key, rule_data) for key, rule_data in data.items()]
    return rules


def read_grouped_rules(dir: str) -> list[Rule]:
    rules: list[Rule] = []

    for filename in os.listdir(dir):
        file_path = os.path.join(dir, filename)
        if not os.path.isfile(file_path):
            continue

        data = read_rule_file(file_path)

        for group_key, group_data in data.items():
            group = group_data["group"]
            group_tags = group_data["tags"]
            group_conditions = (
                build_conditions(group_data["conditions"])
                if "conditions" in group_data
                else None
            )

            for key, rule_data in group.items():
                rule = parse_rule(
                    get_tag_name(group_key, key),
                    rule_data,
                    group_tags,
                    group_conditions,
                )
                rules.append(rule)

    return rules


def read_tag_names(file_path: str) -> dict[str, Localisation]:
    tag_names = read_lines(file_path)
    tag_name_list: dict[str, Localisation] = {}
    for line in tag_names:
        line_split = line.split(":")
        name = line_split[0]
        value = line_split[1]
        if "_ADJ2" in name:
            key = name.replace("_ADJ2", "")
            tagName = tag_name_list[key]
            tagName.adj = process_name(value)
        elif "_ADJ" in name:
            key = name.replace("_ADJ", "")
            tagName = tag_name_list[key]
            tagName.adj = process_name(value)
        else:
            value = process_name(value)
            tagName = Localisation(name=value, adj=None)
            tag_name_list[name] = tagName
    return tag_name_list


def read_dynasties() -> list[str]:
    dynasty_names = read_lines(DYNASTIES_PATH)
    dynasty_names_list = []
    for dynasty in dynasty_names:
        dynasty_names_list.append(dynasty.replace("\n", ""))
    return dynasty_names_list
