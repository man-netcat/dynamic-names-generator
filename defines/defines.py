# === PATHS ===
MOD_PATH = "../"

MODULES_ROOT = "modules"

RULES_DIR = "rules"
SUB_RULES_DIR = "sub_rules"

DYNASTIES_PATH = "data/dynasties.txt"
TAG_NAMES_PATH = "data/tag_names.yml"

# === EVENTS ===
EVENT_NAME = "dynamic_names"

EVENT_SCRIPT_HEADER = """\
### generated events for dynamic names

namespace = {event_name}

country_event = {{
    id = {event_name}.0
    hidden = yes
    is_triggered_only = yes

    immediate = {{
{event_triggers}
    }}

    option = {{
        name = {event_name}.0.a
    }}
}}
"""

TAG_DEPENDANT_EVENT_TEMPLATE = """\
country_event = {{
    id = {event_name}.{id}
    hidden = yes
    is_triggered_only = yes

    trigger = {{
        tag = {tag}
    }}

    immediate = {{
{conditions}
    }}

    option = {{
        name = {event_name}.{id}.a
    }}
}}
"""

TAG_AGNOSTIC_EVENT_TEMPLATE = """\
country_event = {{
    id = {event_name}.{id}
    hidden = yes
    is_triggered_only = yes

    immediate = {{
{conditions}
    }}

    option = {{
        name = {event_name}.{id}.a
    }}
}}
"""

DECISION_TEMPLATE = """\
country_decisions = {{
    update_dynamic_names_decision = {{
        potential = {{ always = yes }}
        allow = {{ always = yes }}
        ai_will_do = {{ factor = 0 }}
        effect = {{ country_event = {{ id = {event_name}.0 }} }}
    }}
}}
"""

MASTER_EVENT_TEMPLATE = """\
### master dispatcher event for dynamic names

namespace = {event_name}

country_event = {{
    id = {event_name}.0
    hidden = yes
    is_triggered_only = yes

    immediate = {{
{module_triggers}
    }}

    option = {{
        name = {event_name}.0.a
    }}
}}
"""

# === FORMATTING ===
FORMAT_TEMPLATES = ["{NAME}", "{NAME_ADJ}", "{DYNASTY}"]
