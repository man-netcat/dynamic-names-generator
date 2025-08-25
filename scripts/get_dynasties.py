import os
from pyradox import parse_dir, parse_file
from pyradox.datatype.tree import Tree

COUNTRIES_PATH = (
    "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV/history/countries"
)
CULTURES_FILE = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV/common/cultures/00_cultures.txt"

dynasties = set()

# Parse all country history files
parsed_countries = parse_dir(COUNTRIES_PATH)

for country_filename, country_data in parsed_countries:
    for top_level_key, top_level_value in country_data.items():

        # Skip if religion is not Muslim
        if top_level_key == "religion" and top_level_value not in [
            "sunni",
            "ibadi",
            "shiite",
        ]:
            break

        # Look for nested structures (like monarch and heir blocks)
        if isinstance(top_level_value, Tree):
            for block_key, block_data in top_level_value.items():
                if block_key in ["monarch", "heir"]:
                    for attribute_key, attribute_value in block_data.items():
                        if attribute_key == "dynasty":
                            dynasties.add(attribute_value)

parsed_cultures = parse_file(CULTURES_FILE)

for culture_group, culture_group_data in parsed_cultures.items():
    for top_level_key, top_level_value in culture_group_data.items():
        if top_level_key == "graphical_culture" and top_level_value != "muslimgfx":
            break

        if isinstance(top_level_value, Tree):
            for block_key, block_data in top_level_value.items():
                print(top_level_value._data)
                # if block_key == "dynasty_names":

# Output the dynasties
# for dynasty_name in sorted(dynasties):
#     print(dynasty_name)
