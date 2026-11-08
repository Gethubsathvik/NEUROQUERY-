"""Deterministic sample e-commerce database used for the demo."""
from __future__ import annotations

import datetime as dt
import random
import sqlite3
from pathlib import Path

DDL = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    segment TEXT NOT NULL,
    signup_date TEXT NOT NULL
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL
);
"""

FIRST = ["Aarav", "Priya", "Rahul", "Ananya", "Liam", "Emma", "Noah", "Olivia", "Lukas", "Sofia",
         "Mia", "Ethan", "Isha", "Karthik", "Meera", "Oliver", "Charlotte", "Jack", "Hannah", "Arjun"]
LAST = ["Sharma", "Reddy", "Patel", "Nair", "Smith", "Johnson", "Brown", "Muller", "Schmidt", "Taylor",
        "Wilson", "Singh", "Kumar", "Rao", "Clark", "Evans", "Walker", "Young", "Hall", "Wright"]
COUNTRIES = ["India", "United States", "United Kingdom", "Germany", "Australia", "Canada"]
COUNTRY_WEIGHTS = [30, 25, 15, 12, 10, 8]
SEGMENTS = ["Consumer", "Small Business", "Enterprise"]
SEGMENT_WEIGHTS = [60, 30, 10]
STATUSES = ["completed", "cancelled", "refunded", "pending"]
STATUS_WEIGHTS = [80, 8, 5, 7]

PRODUCTS = [
    ("Wireless Mouse", "Electronics", 24.99), ("Mechanical Keyboard", "Electronics", 89.0),
    ("USB-C Hub", "Electronics", 39.5), ("Noise-Cancelling Headphones", "Electronics", 199.0),
    ("Webcam HD", "Electronics", 59.0), ("Standing Desk", "Furniture", 349.0),
    ("Ergonomic Chair", "Furniture", 279.0), ("Bookshelf", "Furniture", 119.0),
    ("Desk Lamp", "Furniture", 34.0), ("Monitor Arm", "Furniture", 69.0),
    ("Notebook Pack", "Stationery", 12.5), ("Gel Pens (12)", "Stationery", 8.99),
    ("Planner 2025", "Stationery", 19.0), ("Whiteboard", "Stationery", 45.0),
    ("Sticky Notes", "Stationery", 5.5), ("Python Crash Course", "Books", 32.0),
    ("Deep Learning Handbook", "Books", 64.0), ("Statistics Made Simple", "Books", 28.0),
    ("SQL Cookbook", "Books", 36.0), ("Data Viz Guide", "Books", 41.0),
    ("Yoga Mat", "Fitness", 22.0), ("Resistance Bands", "Fitness", 15.0),
    ("Water Bottle", "Fitness", 18.0), ("Smart Watch", "Fitness", 149.0),
]


def build(path: Path) -> None:
    rnd = random.Random(42)
    tmp = path.with_suffix(".tmp")
    if tmp.exists():
        tmp.unlink()
    conn = sqlite3.connect(tmp)
    conn.executescript(DDL)

    first_day = dt.date(2023, 6, 1)
    last_signup = dt.date(2025, 12, 15)
    last_day = dt.date(2025, 12, 31)

    customers = []
    for cid in range(1, 251):
        signup = first_day + dt.timedelta(days=rnd.randint(0, (last_signup - first_day).days))
        customers.append((
            cid, f"{rnd.choice(FIRST)} {rnd.choice(LAST)}",
            rnd.choices(COUNTRIES, COUNTRY_WEIGHTS)[0],
            rnd.choices(SEGMENTS, SEGMENT_WEIGHTS)[0],
            signup.isoformat(),
        ))
    conn.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customers)
    conn.executemany(
        "INSERT INTO products VALUES (?,?,?,?)",
        [(i + 1, n, c, p) for i, (n, c, p) in enumerate(PRODUCTS)],
    )

    orders, items = [], []
    item_id = 1
    for oid in range(1, 2601):
        cid, _, _, _, signup_s = rnd.choice(customers)
        signup = dt.date.fromisoformat(signup_s)
        odate = signup + dt.timedelta(days=rnd.randint(0, (last_day - signup).days))
        status = rnd.choices(STATUSES, STATUS_WEIGHTS)[0]
        orders.append((oid, cid, odate.isoformat(), status))
        for _ in range(rnd.randint(1, 4)):
            pid = rnd.randint(1, len(PRODUCTS))
            items.append((item_id, oid, pid, rnd.randint(1, 3), PRODUCTS[pid - 1][2]))
            item_id += 1
    conn.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)
    conn.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", items)
    conn.commit()
    conn.close()
    tmp.replace(path)
