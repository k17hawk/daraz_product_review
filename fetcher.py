import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import pandas as pd
from urllib.parse import quote
import time

ua = UserAgent()
HEADERS = {"User-Agent": ua.random, "Accept-Language": "en-US,en;q=0.9"}

def get_search_results(keyword, pages=1):
    """Search Daraz Nepal and return product links with review counts"""
    products = []
    base_url = "https://www.daraz.com.np"
    
    for page in range(1, pages + 1):
        url = f"{base_url}/catalog/?q={quote(keyword)}&page={page}"
        print(f"Scraping search page {page}: {url}")
        
        try:
            response = requests.get(url, headers=HEADERS)
            soup = BeautifulSoup(response.text, "html.parser")
            print(soup)
            
            # Extract product cards
            for item in soup.select('div[data-qa-locator="product-item"]'):
                product_link = item.find("a", href=True)
                if not product_link:
                    continue
                
                # Get review count
                review_element = item.select_one("span.rating__review")
                review_count = int(review_element.get_text(strip=True).split()[0]) if review_element else 0
                
                products.append({
                    "name": item.select_one("div.title").get_text(strip=True) if item.select_one("div.title") else "N/A",
                    "url": f"{base_url}{product_link['href']}",
                    "price": item.select_one("div.price").get_text(strip=True) if item.select_one("div.price") else "N/A",
                    "review_count": review_count
                })
            
            time.sleep(2)  # Be polite with delays
            
        except Exception as e:
            print(f"Error scraping page {page}: {e}")
    
    return products

def get_product_reviews(product_url, max_reviews=100):
    """Scrape all reviews for a single Daraz product"""
    reviews = []
    page = 1
    
    while len(reviews) < max_reviews:
        review_url = f"{product_url.split('?')[0]}?page={page}#review"
        print(f"Scraping review page {page}: {review_url}")
        
        try:
            response = requests.get(review_url, headers=HEADERS)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Check if review section exists
            review_section = soup.select_one("div.mod-reviews")
            if not review_section:
                break
                
            # Extract individual reviews
            for review in review_section.select("div.review-item"):
                reviews.append({
                    "username": review.select_one("div.review-user__name").get_text(strip=True) if review.select_one("div.review-user__name") else "Anonymous",
                    "rating": float(review.select_one("div.ratings").attrs.get("data-score", 0)) if review.select_one("div.ratings") else 0,
                    "date": review.select_one("div.review-date").get_text(strip=True) if review.select_one("div.review-date") else "N/A",
                    "title": review.select_one("div.review-title").get_text(strip=True) if review.select_one("div.review-title") else "N/A",
                    "content": review.select_one("div.review-content").get_text(strip=True) if review.select_one("div.review-content") else "N/A"
                })
            
            # Check for next page
            next_page = soup.select_one("a.next-pagination")
            if not next_page or "disabled" in next_page.get("class", []):
                break
                
            page += 1
            time.sleep(1.5)  # Avoid rate limiting
            
        except Exception as e:
            print(f"Error scraping reviews: {e}")
            break
    
    return reviews

if __name__ == "__main__":
    # Configuration
    SEARCH_KEYWORD = "smartphone"
    MIN_REVIEWS = 3 
    SEARCH_PAGES = 2  
    
    print(f"Searching Daraz Nepal for '{SEARCH_KEYWORD}'...")
    products = get_search_results(SEARCH_KEYWORD, pages=SEARCH_PAGES)
    
    # Filter products with sufficient reviews
    products_with_reviews = [p for p in products if p["review_count"] >= MIN_REVIEWS]
    print(f"Found {len(products_with_reviews)} products with reviews")
    
    # Scrape reviews for each product
    all_reviews = []
    for product in products_with_reviews:
        print(f"\nScraping reviews for: {product['name']}")
        reviews = get_product_reviews(product["url"])
        if reviews:
            for review in reviews:
                review.update({
                    "product_name": product["name"],
                    "product_price": product["price"],
                    "product_url": product["url"]
                })
            all_reviews.extend(reviews)
    
    # Save to CSV
    if all_reviews:
        df = pd.DataFrame(all_reviews)
        filename = f"daraz_{SEARCH_KEYWORD}_reviews.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\nSuccess! Saved {len(all_reviews)} reviews to {filename}")
    else:
        print("\nNo reviews found for the given criteria.")