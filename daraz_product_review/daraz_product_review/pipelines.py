import csv
from itemadapter import ItemAdapter

class CsvExportPipeline:
    def __init__(self):
        self.file = None
        self.writer = None

    def open_spider(self, spider):
        self.file = open('daraz_reviews.csv', 'w', newline='', encoding='utf-8')
        self.writer = csv.DictWriter(self.file, fieldnames=[
            'product_name', 'product_url', 'rating', 
            'review_text', 'review_date', 'reviewer_name'
        ])
        self.writer.writeheader()

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        self.writer.writerow(ItemAdapter(item).asdict())
        return item