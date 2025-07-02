import scrapy
from daraz_product_review.items import DarazReviewItem
import time
import random

class DarazSpider(scrapy.Spider):
    name = 'daraz'
    allowed_domains = ['daraz.com.np']
    
    # Start with category pages
    start_urls = [
        'https://www.daraz.com.np/smartphones/',
        'https://www.daraz.com.np/laptops/',
        'https://www.daraz.com.np/electronics/',
        # Add more categories as needed
    ]

    def parse(self, response):
        # Extract product links from category page
        product_links = response.css('a.product-card::attr(href)').getall()
        
        for product_link in product_links:
            if product_link:
                yield response.follow(
                    product_link, 
                    callback=self.parse_product,
                    meta={'original_url': product_link}
                )
        
        # Pagination (if needed)
        next_page = response.css('a.ant-pagination-next-link::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_product(self, response):
        original_url = response.meta.get('original_url')
        product_name = response.css('h1.pdp-mod-product-badge-title::text').get('').strip()
        
        # Check if reviews tab exists
        reviews_tab = response.css('li.pdp-link-tab-reviews')
        if not reviews_tab:
            return
        
        # Follow the reviews API endpoint (found by inspecting network requests)
        product_id = original_url.split('-')[-1].split('.')[0]
        reviews_api_url = f'https://my.daraz.com.np/pdp/review/getReviewList?itemId={product_id}&pageSize=100'
        
        yield scrapy.Request(
            reviews_api_url,
            callback=self.parse_reviews,
            meta={
                'product_name': product_name,
                'product_url': original_url
            }
        )

    def parse_reviews(self, response):
        product_name = response.meta.get('product_name')
        product_url = response.meta.get('product_url')
        
        try:
            data = response.json()
            if not data.get('model', {}).get('items'):
                return
                
            reviews = data['model']['items']
            
            for review in reviews:
                item = DarazReviewItem()
                item['product_name'] = product_name
                item['product_url'] = product_url
                item['rating'] = review.get('rating')
                item['review_text'] = review.get('reviewContent')
                item['review_date'] = review.get('reviewTime')
                item['reviewer_name'] = review.get('buyerName')
                
                yield item
                
        except Exception as e:
            self.logger.error(f"Error parsing reviews: {e}")