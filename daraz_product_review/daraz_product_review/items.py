import scrapy

class DarazReviewItem(scrapy.Item):
    product_name = scrapy.Field()
    product_url = scrapy.Field()
    rating = scrapy.Field()
    review_text = scrapy.Field()
    review_date = scrapy.Field()
    reviewer_name = scrapy.Field()