import pandas as pd

file_path = "/home/rick/workspace/eu4-resources/countries.csv"
tag_names_path = "/home/rick/workspace/dynamic-names-generator/data/tag_names.txt"

countries_df = pd.read_csv(file_path)

with open(tag_names_path, "r", encoding="utf-8-sig") as f:
    tag_names_content = f.readlines()

included_tags = [line[:3].strip() for line in tag_names_content if not "ADJ" in line]

for _, row in countries_df.iterrows():
    tag = row["Tag"]
    name = row["Country"]
    if tag not in included_tags:
        print(f"{tag}: {name}")
