"""String utility functions for the EU4 Dynamic Names Generator.

This module provides general-purpose string processing and formatting functions.
"""


def process_name(name: str) -> str:
    """Clean and process a name string by removing quotes and whitespace."""
    return name.replace('"', "").replace("\n", "").strip()


def format_as_tag(s: str) -> str:
    """Format a string as an EU4 tag by converting to uppercase and replacing special chars."""
    return s.upper().replace(" ", "_").replace("-", "_").replace("'", "_")


def split_stripped(s: str, sep: str = ",", maxsplit: int = -1) -> list[str]:
    """Split a string and strip whitespace from all parts."""
    return [part.strip() for part in s.split(sep, maxsplit)]


def substitute(template: str, format_str: str, item_name: str) -> str:
    """Replace a format string in a template with the given item name."""
    return template.replace(format_str, item_name)