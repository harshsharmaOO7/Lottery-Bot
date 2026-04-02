import requests
from bs4 import BeautifulSoup
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

def extract_result_number(text):
    match = re.search(r'\b\d{5}\b', text)
    return match.group() if match else text


def extract_pdf(soup):
    links = soup.find_all("a")

    for link in links:
        href = link.get("href", "")
        if ".pdf" in href:
            return href

    return ""


def scrape_site(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        headings = soup.find_all(["h2", "h3"])

        for h in headings:
            text = h.text.strip()

            if "result" in text.lower():
                return {
                    "result": extract_result_number(text),
                    "raw": text,
                    "pdf": extract_pdf(soup),
                    "source": url
                }

    except Exception as e:
        print("Error:", e)

    return None


def get_result(sources):
    for url in sources:
        data = scrape_site(url)
        if data:
            return data
    return None
