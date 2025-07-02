# Scrapy settings for daraz_scraper project

BOT_NAME = 'daraz_product_review'

SPIDER_MODULES = ['daraz_product_review.spiders']
NEWSPIDER_MODULE = 'daraz_product_review.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure Playwright
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# Playwright browser settings
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": False,  # Set to True for production
    "slow_mo": 2000,    # Slow down by 2 seconds between actions
    "args": [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--disable-gpu",
        "--window-size=1920,1080",
    ]
}

# Playwright page settings
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 120000  # 2 minutes
PLAYWRIGHT_CONTEXT_ARGS = {
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "java_script_enabled": True,
    "accept_downloads": False,
    "bypass_csp": True,
    "ignore_https_errors": True,
}

# Delays and concurrency
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# AutoThrottle settings
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = True

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]

# Logging
LOG_LEVEL = 'INFO'

# Headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0',
}

# Disable cookies (can be enabled if needed)
COOKIES_ENABLED = True

# Disable Telnet Console
TELNETCONSOLE_ENABLED = False

# Item pipelines
# ITEM_PIPELINES = {
#    'daraz_scraper.pipelines.DarazScraperPipeline': 300,
# }Z