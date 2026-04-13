import sqlite3
from typing import Optional

class Database:
    def __init__(self, db_path: str = "finance.db"):
        self.db_path = db_path
        self.init_db()

    def get_conn(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    created_at TEXT DEFAULT (date('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    is_waste INTEGER DEFAULT 0,
                    date TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.commit()

    def create_user(self, user_id: int):
        with self.get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            conn.commit()

    def add_transaction(self, user_id, type, amount, category, description="", is_waste=False, date=None):
        if date is None:
            import datetime
            date = datetime.date.today().isoformat()
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO transactions (user_id, type, amount, category, description, is_waste, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, type, amount, category, description, int(is_waste), date)
            )
            conn.commit()

    def get_report(self, user_id, start_date=None, end_date=None):
        query = "SELECT type, amount, category, is_waste FROM transactions WHERE user_id = ?"
        params = [user_id]
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        with self.get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        if not rows:
            return {}
        total_income = 0.0
        total_expense = 0.0
        waste_amount = 0.0
        categories = {}
        for type_, amount, category, is_waste in rows:
            if type_ == 'daromad':
                total_income += amount
            else:
                total_expense += amount
                if is_waste:
                    waste_amount += amount
            categories[category] = categories.get(category, 0) + amount
        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense,
            "waste_amount": waste_amount,
            "categories": categories
        }
