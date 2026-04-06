import csv
import time
import os
from dataclasses import dataclass, asdict, fields

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException



START_URL  = "https://books.toscrape.com/"
MAX_BOOKS  = 10
DELAY      = 0.8
OUTPUT_DIR = "output"



@dataclass
class BookDetail:
    title:       str
    price:       str
    rating:      str
    stock:       str
    upc:         str
    description: str
    url:         str



def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    return driver


def get_book_urls(driver: webdriver.Chrome, max_books: int) -> list[str]:
    driver.get(START_URL)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "article.product_pod"))
    )
    anchors = driver.find_elements(By.CSS_SELECTOR, "article.product_pod h3 > a")
    urls = [a.get_attribute("href") for a in anchors[:max_books]]
    return urls



def scrape_detail(driver: webdriver.Chrome, url: str) -> BookDetail | None:
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_main"))
        )
    except TimeoutException:
        print(f"  [WARN] Timeout on {url}")
        return None

    def text(selector: str, default: str = "N/A") -> str:
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return default

    def attr(selector: str, attribute: str, default: str = "N/A") -> str:
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).get_attribute(attribute)
        except NoSuchElementException:
            return default

    upc = "N/A"
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "table.table tr")
        for row in rows:
            header = row.find_element(By.TAG_NAME, "th").text.strip()
            if header == "UPC":
                upc = row.find_element(By.TAG_NAME, "td").text.strip()
                break
    except NoSuchElementException:
        pass


    description = "N/A"
    try:
        desc_el = driver.find_elements(By.CSS_SELECTOR, "article.product_page > p")
        if desc_el:
            description = desc_el[0].text.strip()[:200]   # truncate to 200 chars
    except NoSuchElementException:
        pass

    rating_class = attr("p.star-rating", "class")
    rating = rating_class.split()[-1] if rating_class != "N/A" else "N/A"

    return BookDetail(
        title       = text("div.product_main h1"),
        price       = text("p.price_color"),
        rating      = rating,
        stock       = text("p.availability"),
        upc         = upc,
        description = description,
        url         = url,
    )

def save_csv(details: list[BookDetail], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    header = [f.name for f in fields(BookDetail)]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(asdict(d) for d in details)
    print(f"[SAVED] {path}  ({len(details)} records)")



def main() -> None:
    print("=" * 60)
    print("  Selenium Detail Page Scraper — Books to Scrape")
    print("=" * 60)

    driver = build_driver()
    details: list[BookDetail] = []

    try:
        print(f"\n[STEP 1] Collecting book URLs from listing page...")
        urls = get_book_urls(driver, MAX_BOOKS)
        print(f"  → Collected {len(urls)} URLs\n")

        print(f"[STEP 2] Visiting each book's detail page...")
        for i, url in enumerate(urls, 1):
            print(f"  [{i}/{len(urls)}] {url.split('/')[-2][:50]}")
            detail = scrape_detail(driver, url)
            if detail:
                details.append(detail)
                print(f"         Title : {detail.title[:45]}")
                print(f"         Price : {detail.price}  |  Rating: {detail.rating}  |  UPC: {detail.upc}")
            time.sleep(DELAY)

    finally:
        driver.quit()

    print()
    save_csv(details, os.path.join(OUTPUT_DIR, "book_details.csv"))
    print(f"\n[DONE] Scraped details for {len(details)} books.")


if __name__ == "__main__":
    main()
