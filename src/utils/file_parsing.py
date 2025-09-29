"""File parsing utilities for the EU4 Dynamic Names Generator.

This module handles parsing of various data files including rules, tag names,
and other configuration files.
"""

import os
from ..classes.Localisation import Localisation
from ..classes.Rule import Rule
from .eu4_parsing import build_conditions, build_tags, read_rule_file
from .name_generation import get_item_name, get_tag_name
from .string_utils import process_name


def read_lines(path: str) -> list[str]:
    """Read lines from a file, filtering out empty lines and comments."""
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def read_modules_config(config_path: str) -> list[str]:
    """Read module names from modules.conf, filtering out comments and empty lines."""
    if not os.path.exists(config_path):
        # Fallback to directory listing if config doesn't exist
        modules_dir = os.path.dirname(config_path)
        modules_root = os.path.join(modules_dir, "modules")
        if os.path.exists(modules_root):
            return sorted(os.listdir(modules_root))
        return []
    
    with open(config_path, encoding="utf-8-sig") as f:
        modules = []
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith("#"):
                modules.append(line)
        return modules


def parse_rule_data(
    key: str, rule_data: dict, parent_tags=None, parent_conditions="", parent_name_adj=None
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

    # Inherit name_adj from parent or use current level's name_adj
    current_name_adj = rule_data["name_adj"] if "name_adj" in rule_data else parent_name_adj

    # Handle grouped rules
    if "group" in rule_data:
        group_name_template = rule_data["name"] if "name" in rule_data else None
        for sub_key in rule_data["group"]:
            sub_rule = rule_data["group"][sub_key]
            if group_name_template and "name" in sub_rule:
                sub_rule["name"] = get_item_name(group_name_template, sub_rule["name"])
            rules.extend(
                parse_rule_data(
                    get_tag_name(key, sub_key), sub_rule, group_tags, group_conditions, current_name_adj
                )
            )
        return rules

    # Handle regular rule
    rule_name = rule_data["name"] if "name" in rule_data else None
    name_adj = rule_data["name_adj"] if "name_adj" in rule_data else current_name_adj
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
    """Parse a single rule file and return a list of rules."""
    data = read_rule_file(file_path)
    all_rules: list[Rule] = []

    for key in data:
        all_rules.extend(parse_rule_data(key, data[key]))

    return all_rules


def parse_rules_dir(dir_path: str) -> list[Rule]:
    """Parse all rule files in a directory and return a combined list of rules."""
    if not dir_path or not os.path.exists(dir_path):
        return []

    all_rules: list[Rule] = []
    for filename in sorted(os.listdir(dir_path)):
        file_path = os.path.join(dir_path, filename)
        if os.path.isfile(file_path):
            all_rules.extend(parse_rule_file(file_path))

    return all_rules


def read_tag_names(file_path: str) -> dict[str, Localisation]:
    """Read and parse tag names from a YAML-style file."""
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