import os

# Path to your EU4 country files
COUNTRIES_PATH = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV/history/countries"

# Iterate over all files in the directory
for filename in os.listdir(COUNTRIES_PATH):
    file_path = os.path.join(COUNTRIES_PATH, filename)
    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="latin-1") as f:
            for line_num, line in enumerate(f, 1):
                if "primary_culture = turkish" in line:
                    print(f"{filename}: line {line_num}: {line.strip()}")
