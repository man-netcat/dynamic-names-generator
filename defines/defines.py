MOD_PATH = "/home/rick/.local/share/Paradox Interactive/Europa Universalis IV/mod/Dynamic-Names"

RULES_PATH = "rules/rules.txt"
SUB_RULES_DIR = "rules/substitution"
GROUPED_RULES_DIR = "rules/grouped"

DYNASTIES_PATH = "data/dynasties.txt"
TAG_NAMES_PATH = "data/tag_names.yml"

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

FORMAT_TEMPLATES = ["{NAME}", "{NAME_ADJ}", "{DYNASTY}"]
