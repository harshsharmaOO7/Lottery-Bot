import json
import os

from scraper import get_result
from parser import parse_data


def load_sources():
    with open("sources.json") as f:
        return json.load(f)


def load_old():
    if os.path.exists("results.json"):
        with open("results.json") as f:
            return json.load(f)
    return {}


def save(data):
    with open("results.json", "w") as f:
        json.dump(data, f, indent=4)


def main():
    sources = load_sources()
    old = load_old()
    new_data = {}

    for state, urls in sources.items():
        raw = get_result(urls)

        if not raw:
            continue

        parsed = parse_data(raw, state)
        key = f"{state}_{parsed['draw'].lower()}"

        # Duplicate check
        if old.get(key, {}).get("result") == parsed["result"]:
            print("No update:", key)
            continue

        new_data[key] = parsed
        print("Updated:", key)

    if new_data:
        save(new_data)
    else:
        print("No new data")


if __name__ == "__main__":
    main()
