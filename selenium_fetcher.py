import time
import csv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import pandas as pd

def init_browser():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(180)  
    return driver

def scroll_to_bottom(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def get_product_links(driver, max_links=20):
    try:
        driver.get("https://www.daraz.com.np/catalog/?q=smartphone")
        time.sleep(4)
        scroll_to_bottom(driver)
        links = []
        elements = driver.find_elements(By.XPATH, "//div[@class='Bm3ON']/div/div/div/div/a")
        for elem in elements:
            link = elem.get_attribute("href")
            if link and link not in links:
                links.append(link)
            if len(links) >= max_links:
                break
        return links
    except TimeoutException:
        print("Timeout occurred while loading the page. Retrying...")
        return get_product_links(driver, max_links)
    except Exception as e:
        print(f"Error getting product links: {e}")
        return []

def extract_reviews_and_details(driver, product_url):
    try:
        driver.get(product_url)
        time.sleep(3)

        product_name = driver.find_element(By.XPATH, "//h1[@class='pdp-mod-product-badge-title']").text
        product_price = driver.find_element(By.XPATH, "//span[@class='pdp-price pdp-price_type_normal pdp-price_color_orange pdp-price_size_xl']").text

        reviews = []
        review_elements = driver.find_elements(By.XPATH, "//div[@class='item']")
        for review_element in review_elements:
            try:
                review_text = review_element.find_element(By.XPATH, ".//div[@class='content']").text
                review_date = review_element.find_element(By.XPATH, ".//span[@class='title right']").text
                review_rating = len(review_element.find_elements(By.XPATH, ".//img[@class='star']"))
                reviews.append({
                    "review_text": review_text,
                    "review_date": review_date,
                    "review_rating": review_rating
                })
            except Exception as e:
                print(f"Error extracting review: {e}")

        return {
            "product_name": product_name,
            "product_url": product_url,
            "product_price": product_price,
            "reviews": reviews
        }
    except Exception as e:
        print(f"Error extracting reviews and details: {e}")
        return None

def save_to_csv(data, filename="product_reviews.csv"):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Product Name", "Product URL", "Product Price", "Review Text", "Review Date", "Review Rating"])
        for entry in data:
            if entry:
                product_name = entry["product_name"]
                product_url = entry["product_url"]
                product_price = entry["product_price"]
                for review in entry["reviews"]:
                    writer.writerow([
                        product_name,
                        product_url,
                        product_price,
                        review["review_text"],
                        review["review_date"],
                        review["review_rating"]
                    ])

def main():
    driver = init_browser()
    try:
        product_links = get_product_links(driver, max_links=20)
        product_data = []
        for link in product_links:
            product_info = extract_reviews_and_details(driver, link)
            if product_info:
                product_data.append(product_info)
        save_to_csv(product_data)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
