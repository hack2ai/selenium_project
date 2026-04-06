import csv
import json
import time
import os
from dataclasses import dataclass, asdict, fields

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException



BASE_URL   = "https://books.toscrape.com/catalogue/"
START_URL  = "https://books.toscrape.com/"
MAX_PAGES  = 5
DELAY      = 1.0
OUTPUT_DIR = "output"


RATING_MAP = {
    "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5
}


@dataclass
class Book:
    title:        str
    price:        str
    rating:       int
    availability: str
    url:          str



def build_driver() -> webdriver.Chrome:

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=options)
    return driver



def scrape_page(driver: webdriver.Chrome, url: str) -> list[Book]:

    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article.product_pod"))
        )
    except TimeoutException:
        print(f"  [WARN] Timed out waiting for books on {url}")
        return []

    articles = driver.find_elements(By.CSS_SELECTOR, "article.product_pod")
    books: list[Book] = []

    for article in articles:
        try:

            title = article.find_element(
                By.CSS_SELECTOR, "h3 > a"
            ).get_attribute("title")


            price = article.find_element(
                By.CSS_SELECTOR, "p.price_color"
            ).text.strip()


            rating_class = article.find_element(
                By.CSS_SELECTOR, "p.star-rating"
            ).get_attribute("class")
            word = rating_class.split()[-1]          # "Three"
            rating = RATING_MAP.get(word, 0)


            availability = article.find_element(
                By.CSS_SELECTOR, "p.availability"
            ).text.strip()


            href = article.find_element(
                By.CSS_SELECTOR, "h3 > a"
            ).get_attribute("href")

            books.append(Book(title, price, rating, availability, href))

        except NoSuchElementException as e:
            print(f"  [SKIP] Missing element: {e.msg[:60]}")

    return books


def get_next_page_url(driver: webdriver.Chrome) -> str | None:

    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, "li.next > a")
        href = next_btn.get_attribute("href")
        return href
    except NoSuchElementException:
        return None



def save_csv(books: list[Book], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    header = [f.name for f in fields(Book)]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(asdict(b) for b in books)
    print(f"[SAVED] CSV  → {path}  ({len(books)} rows)")


def save_json(books: list[Book], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(b) for b in books], f, indent=2, ensure_ascii=False)
    print(f"[SAVED] JSON → {path}  ({len(books)} records)")



def main() -> None:
    print("=" * 60)
    print("  Selenium Web Scraper — Books to Scrape")
    print("=" * 60)

    driver = build_driver()
    all_books: list[Book] = []
    current_url: str | None = START_URL
    page = 1

    try:
        while current_url and page <= MAX_PAGES:
            print(f"\n[PAGE {page}] {current_url}")
            books = scrape_page(driver, current_url)
            all_books.extend(books)
            print(f"  → Found {len(books)} books  (total so far: {len(all_books)})")

            current_url = get_next_page_url(driver)
            page += 1
            if current_url:
                time.sleep(DELAY)

    finally:
        driver.quit()

    if not all_books:
        print("\n[WARN] No data collected.")
        return


    print()
    save_csv(all_books,  os.path.join(OUTPUT_DIR, "books.csv"))
    save_json(all_books, os.path.join(OUTPUT_DIR, "books.json"))


    avg_price = (
        sum(float(b.price.replace("£", "")) for b in all_books) / len(all_books)
    )
    top_rated = sorted(all_books, key=lambda b: b.rating, reverse=True)[:3]

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Total books scraped : {len(all_books)}")
    print(f"  Pages visited       : {page - 1}")
    print(f"  Average price       : £{avg_price:.2f}")
    print(f"  Top 3 rated books:")
    for i, b in enumerate(top_rated, 1):
        print(f"    {i}. {b.title[:50]:<50}  ★{b.rating}  {b.price}")
    print("=" * 60)


if __name__ == "__main__":
    main()
