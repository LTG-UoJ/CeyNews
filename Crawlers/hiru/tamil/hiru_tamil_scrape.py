import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime

BASE_URL = "https://hirunews.lk/tm/{}"
OUTPUT_DIR = "./hiru_tamil"
STATUS_FILE = "./status.json"
FAILED_LOG = "./failed_ids.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# -------------------------------
# Load or initialize status
# -------------------------------
def load_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    return {
        "initial_working_nid": 165334,
        "last_working_nid": 165333
    }

def save_status(status):
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=4)

# -------------------------------
# Retry request (IMPORTANT)
# -------------------------------
def fetch_with_retry(url, retries=3):
    for attempt in range(retries):
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)

            if res.status_code == 200:
                return res

            print(f"[Retry] Status {res.status_code} for {url}")

        except Exception as e:
            print(f"[Retry] Attempt {attempt+1} failed:", e)

        time.sleep(3 + attempt * 2)  # exponential backoff

    return None

# -------------------------------
# Extract article
# -------------------------------
def parse_article(html, url):
    soup = BeautifulSoup(html, "html.parser")

    try:
        headline_tag = soup.select_one("h1.head-title")
        content_container = soup.select_one("#this-article")
        category_tag = soup.select_one(".update-category")
        timestamp_tag = soup.select_one(".update-category + span")

        if not (headline_tag and content_container and category_tag and timestamp_tag):
            return None

        # Remove unwanted elements
        for tag in content_container.find_all(["iframe", "script", "style"]):
            tag.decompose()

        headline = headline_tag.get_text(strip=True)
        content = content_container.get_text(separator="\n", strip=True)
        category = category_tag.get_text(strip=True)
        timestamp = timestamp_tag.get_text(strip=True)

        return {
            "Source": "hirunews",
            "Timestamp": timestamp,
            "Headline": headline,
            "News Content": content,
            "URL": url,
            "Category": category,
            "Parent URL": "https://hirunews.lk/tm/"
        }

    except Exception as e:
        print("Parse error:", e)
        return None

# -------------------------------
# Format date safely
# -------------------------------
def format_date(date_str):
    try:
        # Handle "17 April 2026 - 10:30 AM"
        date_part = date_str.split("-")[0].strip()
        dt = datetime.strptime(date_part, "%d %B %Y")
        return dt.strftime("%Y-%m-%d")
    except:
        return "unknown-date"

# -------------------------------
# Save article
# -------------------------------
def save_article(nid, data):
    date_folder = format_date(data["Timestamp"])

    folder_path = os.path.join(OUTPUT_DIR, date_folder)
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, f"{nid}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# -------------------------------
# Log failed IDs
# -------------------------------
def log_failed(nid):
    with open(FAILED_LOG, "a") as f:
        f.write(f"{nid}\n")

# -------------------------------
# Main scraper
# -------------------------------
def scrape():
    status = load_status()

    start = status["last_working_nid"] + 1
    end = status["initial_working_nid"]

    print(f"Starting from {start} to {end}")

    for nid in range(start, end + 1):
        url = BASE_URL.format(nid)
        print(f"\nScraping: {url}")

        res = fetch_with_retry(url)

        if not res:
            print("Failed after retries")
            log_failed(nid)
            continue

        article = parse_article(res.text, url)

        if article:
            save_article(nid, article)

            status["last_working_nid"] = nid
            save_status(status)

            print(f"Saved {nid}")
        else:
            print("Parsing failed")
            log_failed(nid)

        # Polite scraping delay
        time.sleep(2.5)


if __name__ == "__main__":
    scrape()