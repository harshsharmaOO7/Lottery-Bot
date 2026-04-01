import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def scrape_single_source(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "html.parser")

        # safer extraction
        title_tag = soup.find("h2")
        img_tag = soup.find("img")

        if not title_tag or not img_tag:
            return None

        title = title_tag.text.strip()
        image = img_tag.get("src")

        # basic validation
        if len(title) < 5:
            return None

        return {
            "title": title,
            "image": image,
            "source": url
        }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def get_nagaland_result():
    sources = [
        "https://lotterysambadresult.in/",
        "https://www.lotterysambad.com/",
        "https://lotto.in/nagaland-lottery-result"
    ]

    for url in sources:
        data = scrape_single_source(url)
        if data:
            return data

    return {
        "title": "Result not found",
        "image": "",
        "source": "none"
    }
