import json
from pyradox import parse_file

CULTURES_FILE = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV/common/cultures/00_cultures.txt"
OUTPUT_FILE = "/home/rick/workspace/eu4-resources/cultures.json"

# Parse the EU4 cultures file
parsed_cultures = parse_file(CULTURES_FILE)

# Filter out non-culture keys
cultures = {
    culture_group: [
        top_level_key
        for top_level_key, _ in culture_group_data.items()
        if top_level_key
        not in [
            "country",
            "province",
            "graphical_culture",
            "second_graphical_culture",
            "dynasty_names",
            "male_names",
            "female_names",
        ]
    ]
    for culture_group, culture_group_data in parsed_cultures.items()
}

# Write to JSON
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(cultures, f, ensure_ascii=False, indent=4)

print(f"Cultures written to {OUTPUT_FILE}")
