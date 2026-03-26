import sys
import os

# ⭐ 让Python能找到backend里的模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db_helper import get_sku_info

# 👉 你要查的SKU
sku = "SHTA005501"

result = get_sku_info(sku)

print("查询SKU:", sku)

if result is None:
    print("❌ 数据库中不存在该SKU")
else:
    print("✅ 找到SKU:")
    for k, v in result.items():
        print(f"{k}: {v}")