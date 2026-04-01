import datetime

def parse_nagaland(data):
    return {
        "result": data["title"],
        "image": data["image"],
        "date": str(datetime.date.today()),
        "pdf": ""
    }
