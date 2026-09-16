import os
import json
import time
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# ─────────────────────────────
# CONFIG
# ─────────────────────────────
BASE_URL = "https://www.itnnews.lk/ta"
OUTPUT_DIR = "./itn_tamil"
FAILED_LOG = "./failed_urls.txt"

START_DATE = datetime(2020, 5, 17)
END_DATE   = datetime(2026, 4, 17)

DELAY = 2.5  # safer delay

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

session = requests.Session()
session.headers.update(HEADERS)

# ─────────────────────────────
# FETCH WITH RETRY
# ─────────────────────────────
def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            res = session.get(url, timeout=(5, 10))

            if res.status_code == 200:
                return BeautifulSoup(res.text, "html.parser")

            elif res.status_code == 404:
                return None

            print(f"[Retry] Status {res.status_code} -> {url}")

        except requests.exceptions.Timeout:
            print(f"[Timeout] Attempt {attempt+1} -> {url}")

        except Exception as e:
            print(f"[Error] {url} -> {e}")

        time.sleep(3 + attempt * 2)

    log_failed(url)
    return None

# ─────────────────────────────
# LOG FAILED URLS
# ─────────────────────────────
def log_failed(url):
    with open(FAILED_LOG, "a") as f:
        f.write(url + "\n")

# ─────────────────────────────
# GENERATE DATES
# ─────────────────────────────
def generate_dates(start, end):
    step = -1 if start >= end else 1
    current = start

    while (current >= end if step == -1 else current <= end):
        yield current.strftime("%Y/%m/%d"), current.strftime("%Y-%m-%d")
        current += timedelta(days=step)

# ─────────────────────────────
# GET LISTING URL
# ─────────────────────────────
def get_listing_url(url_date, page):
    if page == 1:
        return f"{BASE_URL}/{url_date}/"
    return f"{BASE_URL}/{url_date}/page/{page}/"

# ─────────────────────────────
# EXTRACT LINKS
# ─────────────────────────────
def extract_article_links(soup):
    return list(set(
        a["href"]
        for a in soup.select("a.p-url[href]")
    ))

# ─────────────────────────────
# EXTRACT CONTENT
# ─────────────────────────────
def extract_content(soup):
    content_div = (
        soup.select_one("div.entry-content")
        or soup.select_one("div.newsContent")
    )

    if not content_div:
        return None

    paragraphs = content_div.find_all("p")

    return "\n\n".join(
        p.get_text(strip=True)
        for p in paragraphs
        if p.get_text(strip=True)
    )

# ─────────────────────────────
# SCRAPE ARTICLE
# ─────────────────────────────
def scrape_article(soup, url):
    def text(el):
        return el.get_text(strip=True) if el else None

    headline = text(soup.select_one("h1.s-title"))
    content = extract_content(soup)

    if not headline or not content:
        return None

    record = {
        "Source": "ITN news",
        "Timestamp": None,
        "Headline": headline,
        "News Content": content,
        "URL": url,
        "Category": text(soup.select_one("a.meta-separate")),
        "Parent URL": None
    }

    # Timestamp
    time_tag = soup.find("time")
    if time_tag:
        record["Timestamp"] = time_tag.get("datetime")

    # Parent URL
    cat_link = soup.select_one("a.meta-separate")
    if cat_link:
        record["Parent URL"] = cat_link.get("href")

    return record

# ─────────────────────────────
# HELPERS
# ─────────────────────────────
def extract_date(timestamp):
    try:
        return datetime.fromisoformat(timestamp).strftime("%Y-%m-%d")
    except:
        return "unknown"

def get_article_id(url):
    return url.rstrip("/").split("/")[-1]

# ─────────────────────────────
# SAVE
# ─────────────────────────────
def save_article(record):
    date_folder = extract_date(record["Timestamp"])
    article_id = get_article_id(record["URL"])

    folder_path = os.path.join(OUTPUT_DIR, date_folder)
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, f"{article_id}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=4)

# ─────────────────────────────
# MAIN
# ─────────────────────────────
def main():
    for url_date, folder_date in generate_dates(START_DATE, END_DATE):
        print(f"\n[DATE] {folder_date}")
        page = 1

        while True:
            listing_url = get_listing_url(url_date, page)
            print(f"  [PAGE {page}] {listing_url}")

            soup = fetch(listing_url)
            if not soup:
                print("  -> No more pages")
                break

            links = extract_article_links(soup)
            print(f"  -> {len(links)} articles found")

            if not links:
                break

            for url in links:
                article_soup = fetch(url)
                if not article_soup:
                    continue

                record = scrape_article(article_soup, url)

                if record:
                    save_article(record)
                    print(f"    Saved: {record['Headline']}")
                else:
                    print(f"    Skipped (invalid content): {url}")
                    log_failed(url)

                time.sleep(DELAY)

            page += 1
            time.sleep(DELAY)


if __name__ == "__main__":
    main()