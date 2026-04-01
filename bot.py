import json
import os

from scraper import get_result_from_sources
from parser import parse_result

def load_sources():
    with open("sources.json") as f:
        return json.load(f)

def load_old_results():
    if os.path.exists("results.json"):
        with open("results.json") as f:
            return json.load(f)
    return {}

def save_results(data):
    with open("results.json", "w") as f:
        json.dump(data, f, indent=4)

def main():
    sources = load_sources()
    old_data = load_old_results()

    new_data = {}

    # Only Nagaland for now (expand later)
    nagaland_sources = sources.get("nagaland", [])

    raw = get_result_from_sources(nagaland_sources)

    if not raw:
        print("No data found")
        return

    parsed = parse_result(raw)

    key = f"nagaland_{parsed['draw'].lower()}"

    # Duplicate check
    if old_data.get(key, {}).get("result") == parsed["result"]:
        print("No new update")
        return

    new_data[key] = parsed

    save_results(new_data)

    print("Updated:", key)


if __name__ == "__main__":
    main()
