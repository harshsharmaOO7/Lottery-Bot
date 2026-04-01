import json
from scraper import get_nagaland_result
from parser import parse_nagaland

def main():
    raw = get_nagaland_result()
    parsed = parse_nagaland(raw)

    data = {
        "nagaland_1pm": parsed
    }

    with open("results.json", "w") as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    main()
