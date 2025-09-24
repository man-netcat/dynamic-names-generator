"""Configuration constants for the EU4 Dynamic Names Generator.

This module contains all configuration constants that control the behavior
of the dynamic names generation process.
"""

# Game event triggers that should trigger dynamic name updates
ON_ACTION_TRIGGERS = [
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

# Global localisation keys for the decision system
GLOBAL_DECISION_KEYS = {
    "title": 'dynamic_names_decision_title:0 "Update Dynamic Names"',
    "desc": 'dynamic_names_decision_desc:0 "Force update dynamic names (e.g. after a government rank change). Happens automatically every 2 in-game years."',
    "tooltip": 'dynamic_names_decision_tooltip:0 "Force update dynamic names (e.g. after a government rank change)."',
}

# Default file encoding for localisation files
LOCALISATION_ENCODING = "utf-8-sig"

# Default file encoding for other files
DEFAULT_ENCODING = "utf-8"

# === NAME FORMATTING ===
FORMAT_TEMPLATES = ["{NAME}", "{NAME_ADJ}", "{DYNASTY}"]
