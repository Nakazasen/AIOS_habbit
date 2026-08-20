
class DataProcessor:
    def process_record(self, record):
        return record.strip()

class AnalyticsEngine(DataProcessor):
    def run_pipeline(self, dataset):
        for item in dataset:
            self.process_record(item)
