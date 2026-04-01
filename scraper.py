import requests
from bs4 import BeautifulSoup

def get_nagaland_result():
    url = "https://lotterysambadresult.in/"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    title = soup.find("h2").text
    image = soup.find("img")["src"]

    return {
        "title": title,
        "image": image
    }
