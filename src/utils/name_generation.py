"""Name generation utilities for the EU4 Dynamic Names Generator.

This module handles the logic for generating different types of names
(country names, dynasty names, etc.) based on rules and templates.
"""

from ..classes.Localisation import Localisation
from .string_utils import substitute


def get_tag_name(tag: str, tag_name: str) -> str:
    """Generate a tag name by combining tag and tag_name."""
    return f"{tag}_{tag_name}"


def get_country_name(rule_name: str, tag_name: tuple[str, Localisation]) -> str:
    """Generate a country name based on the rule and tag information."""
    if "NAME_ADJ" in rule_name:
        return substitute(rule_name, "{NAME_ADJ}", tag_name[1].adj)
    elif "NAME" in rule_name:
        return substitute(rule_name, "{NAME}", tag_name[1].name)
    elif "DYNASTY" in rule_name:
        return None
    return rule_name


def get_dynasty_name(rule_name: str, dynasty_name: str) -> str:
    """Generate a dynasty name based on the rule and dynasty information."""
    if "DYNASTY" in rule_name:
        return substitute(rule_name, "{DYNASTY}", dynasty_name.capitalize())
    return None


def get_item_name(rule_name: str, item_name: str) -> str:
    """Generate an item name by substituting the item name into the rule template."""
    return substitute(rule_name, "{ITEM_NAME}", item_name)