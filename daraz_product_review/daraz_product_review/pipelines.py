import csv

class CsvExportPipeline:
    def open_spider(self, spider):
        self.file = open('daraz_reviews.csv', 'w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)
        self.writer.writerow(['product_name', 'product_url', 'rating', 'review_text', 'review_date', 'reviewer_name'])

    def process_item(self, item, spider):
        self.writer.writerow([
            item.get('product_name'),
            item.get('product_url'),
            item.get('rating'),
            item.get('review_text'),
            item.get('review_date'),
            item.get('reviewer_name')
        ])
        return item

    def close_spider(self, spider):
        self.file.close()
