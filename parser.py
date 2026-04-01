import datetime

def detect_draw(text):
    text = text.lower()

    if "1 pm" in text:
        return "1PM"
    elif "6 pm" in text:
        return "6PM"
    elif "8 pm" in text:
        return "8PM"

    return "unknown"


def parse_result(data):
    return {
        "result": data["title"],
        "draw": detect_draw(data["title"]),
        "image": data["image"],
        "date": str(datetime.date.today()),
        "source": data["source"],
        "pdf": "",
        "verified": False
    }
