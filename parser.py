import datetime

def detect_draw(text):
    text = text.lower()

    if "1 pm" in text or "1pm" in text:
        return "1PM"
    elif "6 pm" in text or "6pm" in text:
        return "6PM"
    elif "8 pm" in text or "8pm" in text:
        return "8PM"

    return "1PM"  # fallback


def parse_data(data, state):
    return {
        "state": state,
        "result": data["result"],
        "draw": detect_draw(data["raw"]),
        "date": str(datetime.date.today()),
        "pdf": data["pdf"],
        "source": data["source"],
        "verified": bool(data["pdf"])
    }
