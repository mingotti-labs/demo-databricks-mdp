# Databricks notebook source
# Seeds Neon's dev branch with synthetic e-commerce data (customers, products,
# orders, order_items) for Phase 3a's Lakeflow Connect pattern. Truncates and
# reseeds on every run -- not incremental, not meant to accumulate.
import random

import psycopg2
from faker import Faker

Faker.seed(42)
random.seed(42)
fake = Faker()

NUM_CUSTOMERS = 200
NUM_PRODUCTS = 50
NUM_ORDERS = 500
PRODUCT_CATEGORIES = ["Electronics", "Home", "Books", "Clothing", "Toys", "Sports"]
ORDER_STATUSES = ["pending", "shipped", "delivered", "cancelled"]

conn = psycopg2.connect(
    host=dbutils.secrets.get("neon-postgres", "host"),
    dbname=dbutils.secrets.get("neon-postgres", "database_name"),
    user=dbutils.secrets.get("neon-postgres", "role_name"),
    password=dbutils.secrets.get("neon-postgres", "password"),
    sslmode="require",
)
conn.autocommit = False
cur = conn.cursor()

# COMMAND ----------

cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price NUMERIC(10, 2) NOT NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(id),
        order_date TIMESTAMP NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL REFERENCES orders(id),
        product_id INTEGER NOT NULL REFERENCES products(id),
        quantity INTEGER NOT NULL,
        unit_price NUMERIC(10, 2) NOT NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
""")
conn.commit()

# COMMAND ----------

# Truncate in FK-safe order, reset identities so ids are predictable each run.
cur.execute("TRUNCATE TABLE order_items, orders, products, customers RESTART IDENTITY CASCADE")
conn.commit()

# COMMAND ----------

customer_ids = []
for _ in range(NUM_CUSTOMERS):
    created = fake.date_time_between(start_date="-2y", end_date="now")
    cur.execute(
        """INSERT INTO customers (first_name, last_name, email, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (fake.first_name(), fake.last_name(), fake.unique.email(), created, created),
    )
    customer_ids.append(cur.fetchone()[0])
conn.commit()

# COMMAND ----------

product_ids = []
for _ in range(NUM_PRODUCTS):
    created = fake.date_time_between(start_date="-2y", end_date="now")
    cur.execute(
        """INSERT INTO products (name, category, price, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (
            fake.catch_phrase(),
            random.choice(PRODUCT_CATEGORIES),
            round(random.uniform(5, 500), 2),
            created,
            created,
        ),
    )
    product_ids.append(cur.fetchone()[0])
conn.commit()

# COMMAND ----------

for _ in range(NUM_ORDERS):
    order_date = fake.date_time_between(start_date="-1y", end_date="now")
    cur.execute(
        """INSERT INTO orders (customer_id, order_date, status, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (
            random.choice(customer_ids),
            order_date,
            random.choice(ORDER_STATUSES),
            order_date,
            order_date,
        ),
    )
    order_id = cur.fetchone()[0]

    for product_id in random.sample(product_ids, k=random.randint(1, 4)):
        cur.execute(
            """INSERT INTO order_items
               (order_id, product_id, quantity, unit_price, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                order_id,
                product_id,
                random.randint(1, 5),
                round(random.uniform(5, 500), 2),
                order_date,
                order_date,
            ),
        )
conn.commit()

# COMMAND ----------

cur.execute("SELECT count(*) FROM customers")
n_customers = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM products")
n_products = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM orders")
n_orders = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM order_items")
n_order_items = cur.fetchone()[0]

cur.close()
conn.close()

dbutils.notebook.exit(
    f"customers={n_customers} products={n_products} orders={n_orders} order_items={n_order_items}"
)
