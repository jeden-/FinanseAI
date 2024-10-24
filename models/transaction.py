from datetime import datetime
from models.database import Database

class Transaction:
    def __init__(self):
        self.db = Database()

    def create_transaction(self, description, amount, type, category, cycle, start_date=None, end_date=None):
        query = """
        INSERT INTO transactions (description, amount, type, category, cycle, start_date, end_date, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db.execute(query, (description, amount, type, category, cycle, start_date, end_date, datetime.now()))

    def get_all_transactions(self):
        query = "SELECT * FROM transactions ORDER BY created_at DESC"
        return self.db.fetch_all(query)

    def get_summary_by_category(self):
        query = """
        SELECT category, SUM(amount) as total
        FROM transactions
        GROUP BY category
        """
        return self.db.fetch_all(query)
