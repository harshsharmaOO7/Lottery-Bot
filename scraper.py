import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def extract_result_text(soup):
    headings = soup.find_all(["h2", "h3", "h4"])

    for h in headings:
        text = h.text.lower()
        if "result" in text:
            return h.text.strip()
    return None


def extract_image(soup):
    images = soup.find_all("img")

    for img in images:
        src = img.get("src", "")
        if "result" in src.lower() or "lottery" in src.lower():
            return src

    return ""


def scrape_single_source(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "html.parser")

        title = extract_result_text(soup)
        image = extract_image(soup)

        if not title:
            return None

        return {
            "title": title,
            "image": image,
            "source": url
        }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def get_result_from_sources(source_list):
    for url in source_list:
        data = scrape_single_source(url)
        if data:
            return data
    return None
