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
    start_urls = ['https://www.daraz.com.np/catalog/?q=smartphone']

    def __init__(self):
        super().__init__()
        # Create directories
        os.makedirs('logs', exist_ok=True)
        os.makedirs('output', exist_ok=True)

        # Initialize counters
        self.step_counter = 0
        self.start_time = datetime.now()
        self.processed_products = 0
        self.failed_products = 0
        self.total_products = 0

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
                'product_id', 'product_name', 'price', 'product_url', 
                'review_id', 'review_text', 'review_rating', 'review_date',
                'reviewer_name', 'verified_purchase', 'review_likes',
                'seller_response', 'response_date', 'response_likes',
                'scraped_at', 'review_images', 'product_specs'
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
            'headless': False,
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
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 300000,
        'PLAYWRIGHT_CONTEXT_ARGS': {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'java_script_enabled': True,
            'ignore_https_errors': True,
            'bypass_csp': True,
        },
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 2,  # Increased delay to avoid blocking
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS': 4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'RETRY_TIMES': 3,  # Increased retry attempts
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

        if page:
            # Take a screenshot for debugging
            await page.screenshot(path='debug_screenshot.png')

            # Log the page content for debugging
            content = await page.content()
            with open('page_content.html', 'w', encoding='utf-8') as f:
                f.write(content)

        self.log_step("📄 HOMEPAGE LOADED", f"Successfully loaded: {response.url}", {
            'status_code': response.status,
            'page_size': len(response.body),
            'title': response.css('title::text').get()
        })

        product_selectors = [
            'a[href*="/products/"]::attr(href)',
            'div[data-qa-locator="product-item"] a::attr(href)',
            '.Bm3ON a::attr(href)',
            '.gridItem--Uy08F a::attr(href)',
            '[class*="product"] a::attr(href)',
            '.item--WJ0dX a::attr(href)',
        ]

        all_product_links = []
        for selector in product_selectors:
            links = response.css(selector).getall()
            if links:
                self.log_step("🔍 SELECTOR SUCCESS", f"Selector '{selector}' found {len(links)} links")
                all_product_links.extend(links)

        unique_links = list(set(link for link in all_product_links if link and 'daraz.com.np' in response.urljoin(link) and '/products/' in response.urljoin(link)))
        self.total_products = len(unique_links)
        self.log_step("🛍️ PRODUCT LINKS PROCESSED", f"Found {self.total_products} unique product links")

        # Process all products
        for i, product_url in enumerate(unique_links):
            # Ensure the URL has the correct scheme
            if product_url.startswith('//'):
                product_url = f'https:{product_url}'
            elif product_url.startswith('/'):
                product_url = f'https://www.daraz.com.np{product_url}'

            self.log_step("🎯 QUEUING PRODUCT", f"Product {i+1}/{self.total_products}: {product_url[:100]}...")

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
                    'total_products': self.total_products,
                },
                dont_filter=True,
                errback=self.handle_error
            )

        if page:
            await page.close()

    async def parse_product(self, response):
        """Parse individual product page with enhanced review extraction"""
        page = response.meta.get('playwright_page')
        product_number = response.meta.get('product_number', 'unknown')
        total_products = response.meta.get('total_products', 'unknown')
        product_id = response.url.split('/')[-1].split('.html')[0]

        self.log_step("🛍️ PRODUCT PAGE LOADED", f"Product #{product_number}/{total_products}: {response.url[:100]}...")

        if page:
            try:
                # Extract basic product info
                product_name = self.extract_product_name(response)
                product_price = self.extract_product_price(response)
                product_rating = self.extract_product_rating(response)

                # Extract all reviews with metadata
                reviews_data = await self.extract_reviews_enhanced(response, page, product_id)

                # Save each review as a separate row in CSV
                for review in reviews_data:
                    self.save_to_csv({
                        'product_id': product_id,
                        'product_name': product_name,
                        'price': product_price,
                        'product_url': response.url,
                        'review_id': review.get('review_id', ''),
                        'review_text': review.get('review_text', ''),
                        'review_rating': review.get('review_rating', ''),
                        'review_date': review.get('review_date', ''),
                        'reviewer_name': review.get('reviewer_name', ''),
                        'verified_purchase': review.get('verified_purchase', False),
                        'review_likes': review.get('review_likes', 0),
                        'seller_response': review.get('seller_response', ''),
                        'response_date': review.get('response_date', ''),
                        'response_likes': review.get('response_likes', 0),
                        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'review_images': '|'.join(review.get('review_images', []) if review.get('review_images') else []),
                        'product_specs': review.get('product_specs', '')
                    })

                self.processed_products += 1
                self.log_step("📊 PROGRESS", 
                            f"Processed {self.processed_products}/{self.total_products} products | "
                            f"Failed: {self.failed_products}")

                yield {
                    'product_id': product_id,
                    'product_name': product_name,
                    'price': product_price,
                    'rating': product_rating,
                    'reviews_count': len(reviews_data),
                    'reviews': reviews_data,
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'product_number': product_number,
                }

            except Exception as e:
                self.failed_products += 1
                self.log_step("❌ PRODUCT PARSING ERROR", f"Failed to parse product: {e}")
            finally:
                if page:
                    await page.close()

    async def extract_reviews_enhanced(self, response, page, product_id):
        """Enhanced review extraction with all metadata and proper waiting"""
        reviews_data = []
        
        if not page:
            self.log_step("⚠️ NO PAGE OBJECT", "Cannot extract reviews without browser page")
            return reviews_data

        try:
            # 1. Ensure reviews section exists and is loaded
            try:
                max_retries = 5
                retry_delay = 5000 
                for attempt in range(max_retries):
                    try:
                        await page.wait_for_selector('.mod-reviews', timeout=30000)  
                        self.log_step("👀 REVIEWS SECTION FOUND", f"Found reviews container (attempt {attempt + 1})")
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            self.log_step("❌ REVIEWS SECTION TIMEOUT", 
                                        f"Reviews section not found after {max_retries} attempts (30s each)")
                            return reviews_data
                        self.log_step("⚠️ REVIEWS RETRY", 
                                    f"Attempt {attempt + 1} failed, retrying in {retry_delay/1000}s...")
                        await page.wait_for_timeout(retry_delay)
                        
                        # Try scrolling to trigger lazy loading
                        await page.evaluate("window.scrollBy(0, 500)")
                        await page.wait_for_timeout(1000)
            except Exception as e:
                self.log_step("❌ REVIEWS SECTION TIMEOUT", "Reviews section not found after 30 seconds")
                return reviews_data

            # 2. Scroll to reviews section and wait
            await page.evaluate("""
                const reviewSection = document.querySelector('.mod-reviews');
                if (reviewSection) {
                    reviewSection.scrollIntoView({behavior: 'smooth'});
                }
            """)
            await page.wait_for_timeout(3000)

            # 3. Try to expand all reviews if pagination exists
            try:
                see_all_button = await page.query_selector('.pdp-review__show-all')
                if see_all_button:
                    await see_all_button.click()
                    await page.wait_for_timeout(5000)  # Wait for reviews to load
                    self.log_step("🔍 CLICKED SEE ALL REVIEWS", "Expanded review section")
            except Exception as e:
                self.log_step("⚠️ SEE ALL BUTTON ERROR", f"Couldn't click button: {str(e)}")

            # 4. Implement scroll-and-wait mechanism to load all reviews
            last_height = await page.evaluate("document.querySelector('.mod-reviews').scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 10
            scroll_timeout = 3000  # 3 seconds between scrolls

            while scroll_attempts < max_scroll_attempts:
                # Scroll to bottom of reviews section
                await page.evaluate("""
                    const reviewSection = document.querySelector('.mod-reviews');
                    if (reviewSection) {
                        reviewSection.scrollTop = reviewSection.scrollHeight;
                    }
                """)
                
                # Wait for new content to load
                await page.wait_for_timeout(scroll_timeout)
                
                # Check if we've reached the end
                new_height = await page.evaluate("document.querySelector('.mod-reviews').scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                    self.log_step("🔄 SCROLL ATTEMPT", 
                                f"Attempt {scroll_attempts}/{max_scroll_attempts} - No new content detected")
                else:
                    scroll_attempts = 0
                    last_height = new_height
                    self.log_step("🔄 SCROLL SUCCESS", "New reviews loaded after scrolling")

            # 5. Wait an additional 5 seconds for any final content to load
            self.log_step("⏳ FINAL WAIT", "Waiting 5 seconds for any remaining content to load")
            await page.wait_for_timeout(5000)

            # 6. Extract all review items
            review_items = await page.query_selector_all('.mod-reviews .item')
            self.log_step("🔍 REVIEW ITEMS FOUND", f"Found {len(review_items)} review items after scrolling")

            for i, item in enumerate(review_items):
                try:
                    review_id = f"{product_id}_review_{i+1}"
                    review_data = {'review_id': review_id}

                    # Extract basic review info
                    content_element = await item.query_selector('.item-content .content')
                    review_data['review_text'] = (await content_element.text_content()).strip() if content_element else "No review text"

                    # Extract rating (count stars)
                    stars = await item.query_selector_all('.container-star .star')
                    review_data['review_rating'] = len(stars) if stars else 0

                    # Extract date
                    date_element = await item.query_selector('.top .title.right')
                    review_data['review_date'] = await date_element.text_content() if date_element else "No date"

                    # Extract reviewer info
                    author_element = await item.query_selector('.middle span:first-child')
                    review_data['reviewer_name'] = await author_element.text_content() if author_element else "Anonymous"

                    # Check if verified purchase
                    verified_element = await item.query_selector('.middle .verify')
                    review_data['verified_purchase'] = bool(verified_element)

                    # Extract likes count
                    likes_element = await item.query_selector('.bottom .left-content span')
                    if likes_element:
                        likes_text = await likes_element.text_content()
                        review_data['review_likes'] = int(re.search(r'\d+', likes_text).group()) if likes_text and re.search(r'\d+', likes_text) else 0
                    else:
                        review_data['review_likes'] = 0

                    # Extract review images
                    image_elements = await item.query_selector_all('.review-image__item .image')
                    review_images = []
                    for img in image_elements:
                        style = await img.get_attribute('style')
                        if style and 'background-image' in style:
                            url_match = re.search(r'url\("?(.*?)"?\)', style)
                            if url_match:
                                review_images.append(url_match.group(1))
                    review_data['review_images'] = review_images

                    # Extract product specs from review
                    specs_element = await item.query_selector('.skuInfo')
                    review_data['product_specs'] = await specs_element.text_content() if specs_element else ""

                    # Extract seller response if exists
                    seller_response_element = await item.query_selector('.seller-reply-wrapper')
                    if seller_response_element:
                        response_text_element = await seller_response_element.query_selector('.item-content--seller-reply .content')
                        review_data['seller_response'] = await response_text_element.text_content() if response_text_element else ""

                        response_date_element = await seller_response_element.query_selector('.item-content--seller-reply .item-title span')
                        if response_date_element:
                            response_date = await response_date_element.text_content()
                            review_data['response_date'] = response_date.replace("Seller Response - ", "").strip()

                        response_likes_element = await seller_response_element.query_selector('.item-content--seller-reply .left-content span')
                        if response_likes_element:
                            likes_text = await response_likes_element.text_content()
                            review_data['response_likes'] = int(re.search(r'\d+', likes_text).group()) if likes_text and re.search(r'\d+', likes_text) else 0

                    reviews_data.append(review_data)

                except Exception as e:
                    self.log_step("⚠️ SINGLE REVIEW ERROR", f"Failed to extract review {i+1}: {str(e)}")
                    continue

            self.log_step("✅ REVIEWS EXTRACTED", f"Collected {len(reviews_data)} reviews with metadata")

        except Exception as e:
            self.log_step("❌ REVIEW EXTRACTION ERROR", f"Failed to extract reviews: {e}")
            # Take screenshot for debugging
            await page.screenshot(path=f'debug_reviews_error_{int(time.time())}.png')

        return reviews_data

    def extract_product_name(self, response):
        """Extract product name with multiple selectors"""
        name_selectors = [
            'h1.pdp-mod-product-badge-title::text',
            'h1[data-spm="product_title"]::text',
            '.pdp-product-title::text',
            'h1::text',
            '.product-title--IaD6Z::text',
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
            '.price--Zls4c::text',
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

    def save_to_csv(self, data):
        """Save product data to CSV file with validation"""
        try:
            # Validate required fields
            required_fields = ['product_id', 'product_name', 'price', 'product_url', 'review_text']
            for field in required_fields:
                if field not in data or not data[field]:
                    self.log_step("⚠️ CSV VALIDATION", f"Missing required field: {field}")
                    return
            
            if self.csv_writer:
                self.csv_writer.writerow(data)
                self.csv_file.flush()
                self.log_step("💾 CSV SAVED", f"Review saved for product: {data['product_name'][:50]}...")
        except Exception as e:
            self.log_step("❌ CSV SAVE ERROR", f"Failed to save to CSV: {e}")
            # Try to recreate CSV file if there's an error
            try:
                self.csv_file.close()
                self.init_csv()
                if self.csv_writer:
                    self.csv_writer.writerow(data)
                    self.csv_file.flush()
            except Exception as e2:
                self.log_step("❌ CSV RECOVERY FAILED", f"Could not recover CSV: {e2}")

    def handle_error(self, failure):
        """Handle request errors"""
        self.failed_products += 1
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
            'total_products': self.total_products,
            'processed_products': self.processed_products,
            'failed_products': self.failed_products,
            'success_rate': f"{self.processed_products/max(1, self.total_products)*100:.1f}%" if self.total_products > 0 else "N/A",
            'csv_file': self.csv_filename
        })

        print(f"\n{'='*80}")
        print("🎉 SCRAPING COMPLETE!")
        print(f"📊 Total Steps: {self.step_counter}")
        print(f"⏱️ Total Time: {total_time}")
        print(f"📦 Products: {self.processed_products}/{self.total_products} processed ({self.failed_products} failed)")
        print(f"📁 Files Created:")
        print(f"   📋 Step Log: {self.step_log_file}")
        print(f"   📄 CSV Output: {self.csv_filename}")
        print(f"{'='*80}")