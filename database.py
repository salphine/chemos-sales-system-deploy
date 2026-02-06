import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json
import os

class Database:
    def __init__(self, db_path="sales_system.db"):
        self.db_path = db_path
        self.connection = None
        self.connect()
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # This enables dictionary-like access
            print(f"Database connected successfully: {self.db_path}")
        except sqlite3.Error as err:
            print(f"Error: {err}")
            # Create in-memory data for demo
            self.connection = None
            
    def get_connection(self):
        if not self.connection:
            self.connect()
        return self.connection
    
    def execute_query(self, query, params=None):
        conn = self.get_connection()
        if conn is None:
            return None
            
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                # Convert sqlite3.Row objects to dictionaries
                return [dict(row) for row in results]
            conn.commit()
            return True
        except Exception as e:
            print(f"Query error: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            return None
        finally:
            cursor.close()
    
    def create_tables(self):
        """Create necessary tables"""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT CHECK(role IN ('admin', 'manager', 'clerk')) DEFAULT 'clerk',
                email TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                price REAL NOT NULL,
                stock_quantity INTEGER DEFAULT 0,
                min_stock_level INTEGER DEFAULT 10,
                max_stock_level INTEGER DEFAULT 100,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE,
                product_id INTEGER,
                quantity INTEGER,
                unit_price REAL,
                total_price REAL,
                tax_amount REAL,
                payment_method TEXT,
                customer_info TEXT,
                user_id INTEGER,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS inventory_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                action TEXT,
                quantity_change INTEGER,
                new_quantity INTEGER,
                user_id INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT,
                tax_rate REAL DEFAULT 16.0,
                currency TEXT DEFAULT 'KES',
                low_stock_alert BOOLEAN DEFAULT 1,
                receipt_template TEXT,
                email_notifications BOOLEAN DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for query in queries:
            self.execute_query(query)
        
        # Create trigger for updated_at in products table
        self.execute_query("""
            CREATE TRIGGER IF NOT EXISTS update_products_timestamp 
            AFTER UPDATE ON products
            BEGIN
                UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        """)
        
        # Create trigger for updated_at in settings table
        self.execute_query("""
            CREATE TRIGGER IF NOT EXISTS update_settings_timestamp 
            AFTER UPDATE ON settings
            BEGIN
                UPDATE settings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        """)
        
        # Insert default admin user
        self.execute_query("""
            INSERT OR IGNORE INTO users (username, password, role, email) 
            VALUES ('admin', 'admin123', 'admin', 'admin@system.com')
        """)
        
        # Insert default settings
        self.execute_query("""
            INSERT OR IGNORE INTO settings (business_name) 
            VALUES ('Salphine Chemos Getaway Resort')
        """)
    
    def get_sample_data(self):
        """Return sample data for demo purposes"""
        products = [
            {'id': 1, 'name': 'Bottled Water', 'category': 'Beverages', 'price': 50.0, 'stock_quantity': 150, 'min_stock_level': 20},
            {'id': 2, 'name': 'Soda', 'category': 'Beverages', 'price': 80.0, 'stock_quantity': 75, 'min_stock_level': 30},
            {'id': 3, 'name': 'Coffee', 'category': 'Beverages', 'price': 150.0, 'stock_quantity': 15, 'min_stock_level': 25},
            {'id': 4, 'name': 'Tea', 'category': 'Beverages', 'price': 120.0, 'stock_quantity': 8, 'min_stock_level': 15},
            {'id': 5, 'name': 'Sandwich', 'category': 'Food', 'price': 300.0, 'stock_quantity': 45, 'min_stock_level': 20},
            {'id': 6, 'name': 'Burger', 'category': 'Food', 'price': 450.0, 'stock_quantity': 25, 'min_stock_level': 15},
            {'id': 7, 'name': 'Pizza', 'category': 'Food', 'price': 800.0, 'stock_quantity': 12, 'min_stock_level': 10},
            {'id': 8, 'name': 'Chicken Wings', 'category': 'Food', 'price': 650.0, 'stock_quantity': 18, 'min_stock_level': 15},
            {'id': 9, 'name': 'Ice Cream', 'category': 'Dessert', 'price': 200.0, 'stock_quantity': 35, 'min_stock_level': 20},
            {'id': 10, 'name': 'Cake Slice', 'category': 'Dessert', 'price': 250.0, 'stock_quantity': 22, 'min_stock_level': 10},
        ]
        
        users = [
            {'id': 1, 'username': 'admin', 'role': 'admin', 'email': 'admin@system.com'},
            {'id': 2, 'username': 'manager1', 'role': 'manager', 'email': 'manager@system.com'},
            {'id': 3, 'username': 'clerk1', 'role': 'clerk', 'email': 'clerk@system.com'},
        ]
        
        return products, users
    
    def backup_database(self, backup_path=None):
        """Create a backup of the SQLite database"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"sales_system_backup_{timestamp}.db"
        
        try:
            source = self.get_connection()
            if source:
                # Create a new connection for the backup
                backup_conn = sqlite3.connect(backup_path)
                source.backup(backup_conn)
                backup_conn.close()
                print(f"Database backup created: {backup_path}")
                return backup_path
        except Exception as e:
            print(f"Backup error: {e}")
            return None
    
    def export_to_csv(self, table_name, export_path=None):
        """Export table data to CSV"""
        if export_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"{table_name}_{timestamp}.csv"
        
        try:
            data = self.execute_query(f"SELECT * FROM {table_name}")
            if data:
                df = pd.DataFrame(data)
                df.to_csv(export_path, index=False)
                print(f"Exported {table_name} to {export_path}")
                return export_path
        except Exception as e:
            print(f"Export error: {e}")
            return None
    
    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            print("Database connection closed")

# Helper functions for compatibility with existing code
if __name__ == "__main__":
    # Test the database connection
    db = Database()
    db.create_tables()
    
    # Test a sample query
    users = db.execute_query("SELECT * FROM users")
    print(f"Users in database: {len(users) if users else 0}")
    
    # Test sample data
    products, _ = db.get_sample_data()
    print(f"Sample products: {len(products)}")
    
    db.close()