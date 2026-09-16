import os
import json
import time
import random
import requests
from bs4 import BeautifulSoup

# ======================
# CONFIG
# ======================
BASE_URL = "https://hirunews.lk/api/fetch_news.php"
BASE_DIR = "data"
SOURCE = "hirunews"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

MAX_RETRIES = 5
BACKOFF_FACTOR = 2

# ======================
# SESSION
# ======================
session = requests.Session()
session.headers.update(HEADERS)

# ======================
# UTILITIES
# ======================

def clean_html(text):
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(separator=" ").strip()


def load_checkpoint():
    path = os.path.join(BASE_DIR, "checkpoint.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_checkpoint(cp):
    os.makedirs(BASE_DIR, exist_ok=True)
    path = os.path.join(BASE_DIR, "checkpoint.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cp, f, indent=2)


def save_article(article, category, date):
    folder = os.path.join(BASE_DIR, category, date)
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, f"{article['id']}.json")

    if os.path.exists(file_path):
        return False

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(article, f, ensure_ascii=False, indent=2)

    return True


def get_start_page(checkpoint, category):
    return checkpoint.get(category, {}).get("last_page", 1)


# ======================
# RETRY LOGIC
# ======================

def fetch_with_retry(url, params):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = session.get(url, params=params, timeout=20)

            if res.status_code == 200:
                return res

            print(f"[WARN] Status {res.status_code} (attempt {attempt})")

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Attempt {attempt}: {e}")

        sleep_time = BACKOFF_FACTOR ** attempt
        print(f"Retrying in {sleep_time}s...")
        time.sleep(sleep_time)

    return None


# ======================
# SCRAPER
# ======================

def scrape(category="Sports", max_pages=2000):
    checkpoint = load_checkpoint()
    start_page = get_start_page(checkpoint, category)

    print(f"Start | Category={category} | Resume page={start_page}")

    for page in range(start_page, max_pages + 1):

        params = {
            "page": page,
            "category": category
        }

        res = fetch_with_retry(BASE_URL, params)

        if res is None:
            print(f"[SKIP] Page {page} failed after retries")
            continue

        try:
            data = res.json()
        except Exception:
            print("[ERROR] Invalid JSON response")
            continue

        if not data:
            print("No more data. Stopping.")
            break

        new_articles = 0

        for item in data:
            try:
                art_id = int(item["sinhala_art_id"])
                date = item["sinhala_added_date"].split(" ")[0]

                article = {
                    "Source": SOURCE,
                    "Timestamp": item.get("sinhala_added_date", ""),
                    "Headline": item.get("sinhala_title", ""),
                    "News Content": clean_html(item.get("sinhala_story", "")),
                    "URL": "https://hirunews.lk/" + item.get("seourltitle", ""),
                    "Category": category,
                    "Parent URL": f"https://hirunews.lk/news_listing.php?category={category}",
                    "id": art_id
                }

                saved = save_article(article, category, date)

                if saved:
                    new_articles += 1

            except Exception as e:
                print(f"[SKIP ITEM] {e}")
                continue

        print(f"Page {page} done | New articles: {new_articles}")

        # save checkpoint
        checkpoint[category] = {
            "last_page": page + 1
        }
        save_checkpoint(checkpoint)

        if new_articles == 0:
            print("No new articles. Likely reached old data. Stopping.")
            break

        # polite delay (important for avoiding blocking)
        time.sleep(1 + random.uniform(0.5, 1.5))


# ======================
# RUN
# ======================

if __name__ == "__main__":
    scrape(category="International", max_pages=100000)