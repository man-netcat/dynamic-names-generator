"""EU4-specific parsing and generation utilities.

This module handles EU4-specific parsing tasks, condition building,
and event generation utilities.
"""

import pyradox


def build_conditions(tree) -> str:
    """Build a condition string from a parsed tree structure."""
    return " ".join(map(str.strip, str(tree).split("\n"))).strip()


def build_tags(tree) -> list[str]:
    """Extract tags from a parsed tree structure."""
    return list(tree["tags"].values()) if tree and "tags" in tree else []


def build_if_block(
    limit: str = None,
    tag: str = None,
    event_name: str = None,
    event_id: int = None,
    override_name: str = None,
) -> str:
    """Build an EU4 if-block for events with the specified conditions and actions."""
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
        actions.append(f"country_event = {{ id = {event_name}.{event_id} }}")

    actions_str = " ".join(actions)

    return f"        if = {{ limit = {{ {limit_str} }} {actions_str} }}"


def read_rule_file(path: str):
    """Parse an EU4 rule file using pyradox."""
    return pyradox.txt.parse_file(path=path, game="EU4", path_relative_to_game=False)