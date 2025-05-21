# database.py
import sqlite3
from sqlite3 import Error

DATABASE = "app.db"


def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn
    except Error as e:
        print(e)
    return conn


def create_tables():
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()

            # Создание таблицы users
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                login TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                fio TEXT,
                phone TEXT,
                email TEXT,
                passport TEXT,
                adress TEXT
            )
            """)

            # Создание таблицы products
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT
            )
            """)

            conn.execute("""
                        CREATE TABLE IF NOT EXISTS reports (
                            id INTEGER PRIMARY KEY,
                            client_id INTEGER UNIQUE NOT NULL,
                            income REAL NOT NULL,
                            expenses REAL NOT NULL,
                            FOREIGN KEY (client_id) REFERENCES users(id)
                        )
                    """)

            conn.commit()
            print("Tables created successfully")
        except Error as e:
            print(e)
        finally:
            conn.close()


# Вызываем создание таблиц при импорте
create_tables()