import sqlite3

def init_db():
    conn = sqlite3.connect("ecommerce.db")
    cur = conn.cursor()

    # 创建商品表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS goods (
        name TEXT PRIMARY KEY,
        stock INTEGER
    )
    """)

    # 初始化库存
    goods = [
        ("phone", 10),
        ("earphone", 20),
        ("laptop", 5)
    ]
    cur.executemany("INSERT OR REPLACE INTO goods (name, stock) VALUES (?, ?)", goods)

    # 创建订单表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        status TEXT
    )
    """)

    # 初始订单
    orders = [
        ("1001", "ordered"),
        ("1002", "shipped"),
        ("1003", "delivered")
    ]
    cur.executemany("INSERT OR REPLACE INTO orders (id, status) VALUES (?, ?)", orders)

    conn.commit()
    conn.close()

    print("数据库初始化完成 ecommerce.db")

if __name__ == "__main__":
    init_db()
