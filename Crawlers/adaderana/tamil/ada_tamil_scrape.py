from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup as soup
import requests, json, time, os, re
from datetime import datetime
import time

def _date_folder_from_timestamp(ts: str) -> str:
    if not ts:
        return "unknown_date"
    cleaned = " ".join(str(ts).strip().split())
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", cleaned)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", cleaned)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if a > 12 and b <= 12:
            d, mo = a, b
        elif b > 12 and a <= 12:
            d, mo = b, a
        else:
            mo, d = a, b
        try:
            return f"{datetime(y, mo, d):%Y-%m-%d}"
        except ValueError:
            pass
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d, %Y %I:%M %p",
                "%b %d, %Y %I:%M %p", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.search(r"\b([A-Za-z]{3,9})\s+(\d{1,2}),\s*(\d{4})\b", cleaned)
    if m:
        candidate = f"{m.group(1)} {m.group(2)}, {m.group(3)}"
        for fmt in ("%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(candidate, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return "unknown_date"


def get_session_via_selenium(seed_url: str) -> requests.Session:
    """Launch browser once, solve Sucuri challenge, return a requests session with valid cookies."""
    print("Launching browser to solve Sucuri challenge...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(seed_url)

    WebDriverWait(driver, 15).until(
        lambda d: "You are being redirected" not in d.title
    )
    time.sleep(2)  # let cookies settle

    # Transfer cookies from browser → requests session
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://tamil.adaderana.lk/",
        "Accept-Language": "en-US,en;q=0.9",
    })
    for cookie in driver.get_cookies():
        session.cookies.set(cookie["name"], cookie["value"])

    driver.quit()
    
    print("Browser closed. Switching to requests.\n")
    return session


def fetch_with_retry(session: requests.Session, url: str, retries=3, backoff=5):
    """Fetch URL with retry logic. Returns response or None."""
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=10, allow_redirects=True)
            # Sucuri challenge page comes back as 200 but with JS redirect title
            if "You are being redirected" in response.text:
                print(f"  Session expired (Sucuri challenge). Re-authenticating...")
                return None  # signal to re-auth
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"  Attempt {attempt}/{retries} failed: {e}")
            time.sleep(backoff * attempt)
    return None


# ── MAIN ─────────────────────────────────────────────────────────────────────

with open("status.json", "r") as f:
    status = json.load(f)

start = status['last_working_nid']
end   = status['initial_working_nid']
print(f"Starting from NID: {start}, up to: {end}")

start_time = time.time()

SEED_URL = f"https://tamil.adaderana.lk/news.php?nid={start}"
session  = get_session_via_selenium(SEED_URL)

SLEEP_BETWEEN = 2      # seconds between requests (was 3)
REAUTH_EVERY  = 1000    # re-solve Sucuri challenge every N articles

for i in range(start, end):
    current_url = f'https://tamil.adaderana.lk/news.php?nid={i}'

    # Periodically refresh session to avoid Sucuri cookie expiry
    if (i - start) > 0 and (i - start) % REAUTH_EVERY == 0:
        print(f"\n[{i}] Refreshing session after {REAUTH_EVERY} requests...")
        session = get_session_via_selenium(current_url)

    response = fetch_with_retry(session, current_url)

    if response is None:
        # Session expired mid-run → re-auth immediately
        session  = get_session_via_selenium(current_url)
        response = fetch_with_retry(session, current_url)
        if response is None:
            print(f"[{i}] Skipping after failed re-auth.")
            continue

    page_soup    = soup(response.content, "html.parser")
    headline_tag = page_soup.find("h2",  {"class": "completeNewsTitle"})
    ts_tag       = page_soup.find("p",   {"class": "newsDateStamp"})
    content_tag  = page_soup.find("div", {"class": "newsContent"})

    if not any([headline_tag, ts_tag, content_tag]):
        print(f"[{i}] No article found, skipping.")
        continue

    if not all([headline_tag, ts_tag, content_tag]):
        print(f"[{i}] Missing some fields, skipping.")
        continue

    headline = headline_tag.get_text()
    ts       = " ".join(ts_tag.get_text().strip().split())

    news = content_tag.get_text().strip()
    
    # Clean up messy line endings → uniform double newline between paragraphs
    news = re.sub(r'\r\n|\r', '\n', news)        # normalize \r\n and \r to \n
    news = re.sub(r'\n{3,}', '\n\n', news)        # collapse 3+ newlines to 2
    news = re.sub(r'[ \t]+\n', '\n', news)        # remove trailing spaces before newline
    news = re.sub(r'\s+', ' ', news).strip()       # remove leading spaces after newline
    news = news.strip()

    if headline and news:
        news_model = {
            "Source":       "Adaderana",
            "Timestamp":    ts,
            "Headline":     headline,
            "News Content": news,
            "URL":          current_url,
            "Category":     None,
            "Parent URL":   None,
        }

        date_folder = _date_folder_from_timestamp(ts)
        out_dir     = os.path.join(".", "adaderana_tamil", date_folder)
        os.makedirs(out_dir, exist_ok=True)

        with open(os.path.join(out_dir, f"{i}.json"), "w", encoding="utf8") as f:
            json.dump(news_model, f, ensure_ascii=False, indent=4)

        status["last_working_nid"] = i
        with open("status.json", "w") as f:
            json.dump(status, f, indent=4)

        print(f"[{i}] ✓ Saved: {headline[:60]}")
        
    time.sleep(SLEEP_BETWEEN)
    
elapsed = time.time() - start_time

hours   = int(elapsed // 3600)
minutes = int((elapsed % 3600) // 60)
seconds = int(elapsed % 60)

print(f"\nDone! {hours}h {minutes}m {seconds}s for {end - start} articles")
print(f"Average: {elapsed / (end - start):.2f} sec/article")