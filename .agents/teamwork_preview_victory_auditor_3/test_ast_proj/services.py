
class BaseService:
    def log_event(self, event):
        pass

class PaymentService(BaseService):
    def process_payment(self, amount):
        self.log_event(amount)
