import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database.db")


def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def get_sku_info(sku):
    sku = str(sku).strip().upper()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SKU, CLIENT_SKU, 长, 宽, 高, 最长边
        FROM sku_info
        WHERE CLIENT_SKU = ? OR SKU = ?
    """, (sku, sku))

    row = cursor.fetchone()
    conn.close()

    print("输入SKU:", repr(sku))

    if row is None:
        return None

    return {
        "SKU": row[0],
        "CLIENT_SKU": row[1],
        "长": row[2],
        "宽": row[3],
        "高": row[4],
        "最长边": row[5]
    }