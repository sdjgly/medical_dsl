import sqlite3
import os

def init_db(db_path=None):
    """初始化数据库，支持自定义路径"""
    if db_path is None:
        # 默认路径为项目根目录下的 database/ecommerce.db
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        db_path = os.path.join(project_root, "database", "ecommerce.db")
    
    # 确保数据库目录存在
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    conn = sqlite3.connect(db_path)
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

    print(f"数据库初始化完成: {db_path}")

if __name__ == "__main__":
    init_db()