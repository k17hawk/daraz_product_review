import scrapy
from scrapy.http import Request
import re
import time
import json
import os
import csv
from datetime import datetime

class DarazDetailedSpider(scrapy.Spider):
    name = 'daraz'
    allowed_domains = ['daraz.com.np']
    start_urls = ['https://www.daraz.com.np/laptops/']

    def __init__(self):
        super().__init__()
        # Create directories
        os.makedirs('logs', exist_ok=True)
        os.makedirs('screenshots', exist_ok=True)
        os.makedirs('html_dumps', exist_ok=True)
        os.makedirs('output', exist_ok=True)

        # Initialize step counter
        self.step_counter = 0
        self.start_time = datetime.now()

        # Log file for detailed steps
        self.step_log_file = f'logs/detailed_steps_{int(time.time())}.log'

        # CSV file for output
        self.csv_filename = f'output/daraz_products_{int(time.time())}.csv'
        self.csv_file = None
        self.csv_writer = None

        # Initialize CSV file
        self.init_csv()

        self.log_step("🚀 SPIDER INITIALIZATION", "Spider started successfully")

    def init_csv(self):
        """Initialize CSV file with headers"""
        try:
            self.csv_file = open(self.csv_filename, 'w', newline='', encoding='utf-8')
            fieldnames = [
                'product_name', 'price', 'url', 'reviews_count',
                'review_1', 'review_2', 'review_3', 'review_4', 'review_5',
                'rating', 'scraped_at', 'product_number', 'source'
            ]
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
            self.csv_writer.writeheader()
            self.log_step("📄 CSV INITIALIZED", f"CSV file created: {self.csv_filename}")
        except Exception as e:
            self.log_step("❌ CSV INIT ERROR", f"Failed to initialize CSV: {e}")

    custom_settings = {
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--allow-running-insecure-content',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        },
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 180000,
        'PLAYWRIGHT_CONTEXT_ARGS': {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'java_script_enabled': True,
            'ignore_https_errors': True,
            'bypass_csp': True,
        },
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'RETRY_TIMES': 2,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 403, 404],
        'LOG_LEVEL': 'INFO',
    }

    def log_step(self, step_name, description, extra_data=None):
        """Log each step with timestamp and details"""
        self.step_counter += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elapsed = datetime.now() - self.start_time

        log_entry = {
            'step': self.step_counter,
            'timestamp': timestamp,
            'elapsed_seconds': elapsed.total_seconds(),
            'step_name': step_name,
            'description': description,
            'extra_data': extra_data
        }

        self.logger.info(f"STEP {self.step_counter} | {step_name} | {description}")

        with open(self.step_log_file, 'a', encoding='utf-8') as f:
            f.write(f"{json.dumps(log_entry, indent=2)}\n")

        print(f"\n{'='*80}")
        print(f"STEP {self.step_counter}: {step_name}")
        print(f"TIME: {timestamp} (Elapsed: {elapsed.total_seconds():.1f}s)")
        print(f"DESC: {description}")
        if extra_data:
            print(f"DATA: {extra_data}")
        print(f"{'='*80}")

    def start_requests(self):
        """Generate initial request"""
        self.log_step("🌐 CREATING INITIAL REQUEST", f"Preparing to visit: {self.start_urls[0]}")

        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse_homepage,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_page_methods': [
                        {'method': 'wait_for_load_state', 'args': ['networkidle']},
                    ],
                },
                dont_filter=True,
                errback=self.handle_error
            )

    async def parse_homepage(self, response):
        """Parse homepage to find product links"""
        page = response.meta.get('playwright_page')

        self.log_step("📄 HOMEPAGE LOADED", f"Successfully loaded: {response.url}", {
            'status_code': response.status,
            'page_size': len(response.body),
            'title': response.css('title::text').get()
        })

        if page:
            try:
                screenshot_path = f'screenshots/step_{self.step_counter}_homepage.png'
                await page.screenshot(path=screenshot_path, full_page=True)
                self.log_step("📸 HOMEPAGE SCREENSHOT", f"Screenshot saved: {screenshot_path}")
            except Exception as e:
                self.log_step("❌ SCREENSHOT ERROR", f"Failed to take screenshot: {e}")

        product_selectors = [
            'a[href*="/products/"]::attr(href)',
            'div[data-qa-locator="product-item"] a::attr(href)',
            '.c16H9d a::attr(href)',
            '.gridItem a::attr(href)',
            '[class*="product"] a::attr(href)',
            '.item a::attr(href)',
        ]

        all_product_links = []
        for selector in product_selectors:
            links = response.css(selector).getall()
            if links:
                self.log_step("🔍 SELECTOR SUCCESS", f"Selector '{selector}' found {len(links)} links")
                all_product_links.extend(links)

        unique_links = list(set(link for link in all_product_links if link and 'daraz.com.np' in response.urljoin(link) and '/products/' in response.urljoin(link)))
        self.log_step("🛍️ PRODUCT LINKS PROCESSED", f"Found {len(unique_links)} unique product links")

        for i, product_url in enumerate(unique_links[:20]):  # Process up to 20 products
            self.log_step("🎯 QUEUING PRODUCT", f"Product {i+1}: {product_url[:100]}...")

            yield Request(
                url=product_url,
                callback=self.parse_product,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_page_methods': [
                        {'method': 'wait_for_load_state', 'args': ['networkidle']},
                    ],
                    'product_number': i + 1,
                },
                dont_filter=True,
                errback=self.handle_error
            )

        if page:
            await page.close()

    async def parse_product(self, response):
        """Parse individual product page with improved review extraction"""
        page = response.meta.get('playwright_page')
        product_number = response.meta.get('product_number', 'unknown')

        self.log_step("🛍️ PRODUCT PAGE LOADED", f"Product #{product_number}: {response.url[:100]}...")

        if page:
            try:
                has_reviews = await self.check_for_reviews(page)
                if not has_reviews:
                    self.log_step("❌ NO REVIEWS", f"Skipping product without reviews: {response.url}")
                    if page:
                        await page.close()
                    return

                screenshot_path = f'screenshots/step_{self.step_counter}_product_{product_number}.png'
                await page.screenshot(path=screenshot_path, full_page=True)
                self.log_step("📸 PRODUCT SCREENSHOT", f"Product screenshot: {screenshot_path}")
            except Exception as e:
                self.log_step("❌ PRODUCT SCREENSHOT ERROR", f"Failed: {e}")

        product_name = self.extract_product_name(response)
        product_price = self.extract_product_price(response)
        product_rating = self.extract_product_rating(response)

        reviews = await self.extract_reviews_enhanced(response, page)

        self.save_to_csv({
            'product_name': product_name,
            'price': product_price,
            'url': response.url,
            'reviews_count': len(reviews),
            'review_1': reviews[0] if len(reviews) > 0 else '',
            'review_2': reviews[1] if len(reviews) > 1 else '',
            'review_3': reviews[2] if len(reviews) > 2 else '',
            'review_4': reviews[3] if len(reviews) > 3 else '',
            'review_5': reviews[4] if len(reviews) > 4 else '',
            'rating': product_rating,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'product_number': product_number,
            'source': 'homepage'
        })

        if page:
            await page.close()

        yield {
            'url': response.url,
            'product_name': product_name,
            'price': product_price,
            'rating': product_rating,
            'reviews_count': len(reviews),
            'reviews': reviews,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'product_number': product_number,
        }

    async def check_for_reviews(self, page):
        """Check if the product page has reviews"""
        try:
            review_elements = await page.query_selector_all('.review-content, .review-item .text')
            return len(review_elements) > 0
        except Exception as e:
            self.log_step("❌ CHECK REVIEWS ERROR", f"Error checking for reviews: {e}")
            return False

    def extract_product_name(self, response):
        """Extract product name with multiple selectors"""
        name_selectors = [
            'h1.pdp-mod-product-badge-title::text',
            'h1[data-spm="product_title"]::text',
            '.pdp-product-title::text',
            'h1::text',
            '.product-title::text',
            '[data-testid="product-title"]::text',
        ]

        for selector in name_selectors:
            name = response.css(selector).get()
            if name and name.strip():
                self.log_step("✅ PRODUCT NAME FOUND", f"Name: {name.strip()[:100]}...")
                return name.strip()

        self.log_step("❌ PRODUCT NAME NOT FOUND", "Could not extract product name")
        return "Not found"

    def extract_product_price(self, response):
        """Extract product price with multiple selectors"""
        price_selectors = [
            '.pdp-price.pdp-price_type_normal.pdp-price_color_orange.pdp-price_size_xl::text',
            '.notranslate::text',
            '[data-spm="price"]::text',
            '.price::text',
            '.current-price::text',
            '[class*="price"]::text',
        ]

        for selector in price_selectors:
            price = response.css(selector).get()
            if price and 'Rs' in price:
                self.log_step("💰 PRODUCT PRICE FOUND", f"Price: {price.strip()}")
                return price.strip()

        self.log_step("❌ PRODUCT PRICE NOT FOUND", "Could not extract product price")
        return "Not found"

    def extract_product_rating(self, response):
        """Extract product rating"""
        rating_selectors = [
            '.score-average::text',
            '[data-spm="rating"]::text',
            '.rating::text',
            '[class*="rating"]::text',
        ]

        for selector in rating_selectors:
            rating = response.css(selector).get()
            if rating and rating.strip():
                self.log_step("⭐ PRODUCT RATING FOUND", f"Rating: {rating.strip()}")
                return rating.strip()

        return "No rating"

    async def extract_reviews_enhanced(self, response, page):
        """Enhanced review extraction with better selectors and interaction"""
        reviews = []

        if page:
            try:
                await page.evaluate("""
                    const reviewSection = document.querySelector('.reviews-section');
                    if (reviewSection) {
                        reviewSection.scrollIntoView({behavior: 'smooth'});
                    }
                """)
                await page.wait_for_timeout(2000)

                await page.click('.reviews-tab', timeout=5000)
                await page.wait_for_timeout(2000)

                review_selectors = [
                    '.review-content::text',
                    '.review-item .text::text',
                ]

                for selector in review_selectors:
                    texts = await page.query_selector_all(selector)
                    for text in texts:
                        review = await text.get_attribute('textContent')
                        if review and len(review.strip()) > 15:
                            reviews.append(review.strip())

                reviews = list(dict.fromkeys(reviews))[:5]

            except Exception as e:
                self.log_step("❌ PAGE INTERACTION ERROR", f"Error: {e}")

        return reviews

    def save_to_csv(self, data):
        """Save product data to CSV file"""
        try:
            if self.csv_writer:
                self.csv_writer.writerow(data)
                self.csv_file.flush()
                self.log_step("💾 CSV SAVED", f"Product saved: {data['product_name'][:50]}...")
        except Exception as e:
            self.log_step("❌ CSV SAVE ERROR", f"Failed to save to CSV: {e}")

    def handle_error(self, failure):
        """Handle request errors"""
        self.log_step("❌ REQUEST ERROR", f"Request failed: {failure.value}", {
            'url': failure.request.url,
            'error_type': type(failure.value).__name__,
            'error_message': str(failure.value)
        })

    def closed(self, reason):
        """Called when spider closes"""
        if self.csv_file:
            self.csv_file.close()
            self.log_step("📄 CSV CLOSED", f"CSV file closed: {self.csv_filename}")

        end_time = datetime.now()
        total_time = end_time - self.start_time

        self.log_step("🏁 SPIDER FINISHED", f"Spider closed. Reason: {reason}", {
            'total_steps': self.step_counter,
            'total_time_seconds': total_time.total_seconds(),
            'csv_file': self.csv_filename
        })

        print(f"\n{'='*80}")
        print("🎉 SCRAPING COMPLETE!")
        print(f"📊 Total Steps: {self.step_counter}")
        print(f"⏱️ Total Time: {total_time}")
        print(f"📁 Files Created:")
        print(f"   📋 Step Log: {self.step_log_file}")
        print(f"   📄 CSV Output: {self.csv_filename}")
        print(f"   📸 Screenshots: screenshots/")
        print(f"{'='*80}")
