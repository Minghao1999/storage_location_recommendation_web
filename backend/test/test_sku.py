import os
import random
import pandas as pd

from sku_finder import find_location_by_sku
from data_loader import load_data

# ==============================
# 📁 自动找到今天的 inventory 文件
# ==============================
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
data_dir = "gdrive/data"

files = [f for f in os.listdir(data_dir) if "inventory" in f]

if not files:
    raise Exception("❌ 没找到 inventory 文件")

# 取最新的
latest_inventory = sorted(files)[-1]
inventory_path = os.path.join(data_dir, latest_inventory)

# empty 文件同理
empty_files = [f for f in os.listdir(data_dir) if "empty" in f]
latest_empty = sorted(empty_files)[-1]
empty_path = os.path.join(data_dir, latest_empty)

print("使用文件:")
print("inventory:", inventory_path)
print("empty:", empty_path)

# ==============================
# 📊 加载数据
# ==============================
df, inventory_all = load_data(inventory_path, empty_path)

# ==============================
# 🎯 从 C列抽 SKU
# ==============================
inventory = pd.read_excel(inventory_path)

# C列（客户SKU）
client_sku = (
    inventory.iloc[:, 2]
    .astype(str)
    .str.strip()
    .str.upper()
)

# A列（京东SKU）
jd_sku = (
    inventory.iloc[:, 0]
    .astype(str)
    .str.strip()
    .str.upper()
)

# 👉 只保留FG开头（防止脏数据）
jd_sku = jd_sku[jd_sku.str.startswith("FG")]

# 👉 合并两个SKU池
sku_list = pd.concat([client_sku, jd_sku])

# 👉 清洗
sku_list = sku_list[sku_list != ""]
sku_list = sku_list.dropna().unique()

# 去掉空值
sku_list = sku_list[sku_list != ""]
sku_list = sku_list.dropna().unique()

# 随机抽100个（不够就全用）
sample_size = min(100, len(sku_list))
test_skus = random.sample(list(sku_list), sample_size)

print(f"\n随机抽取 {sample_size} 个SKU测试\n")

# ==============================
# 🧪 测试逻辑
# ==============================
error_A = 0
error_B = 0
error_full = 0

for sku in test_skus:

    location, item_len, space = find_location_by_sku(df, inventory_all, sku)

    print(f"SKU: {sku}")
    print(f"推荐: {location}")

    if not location:
        print("⚠️ 无推荐")
        print("-" * 30)
        continue

    # ⭐ 模拟上架（关键！）
    parts = location.split("-")
    A = int(parts[0][1:])
    R = int(parts[1][1:])
    L = int(parts[2][1:])
    B = int(parts[3][1:])   # ⭐必须有B

    new_row = {
        "A": A,
        "R": R,
        "L": L,
        "B": B,
        "长": item_len,
        "宽": 0,
        "高": 0,
        "status": "occupied",
        "SKU_ALL": sku
    }

    df.loc[len(df)] = new_row

    parts = location.split("-")
    A = int(parts[0][1:])
    R = int(parts[1][1:])
    L = int(parts[2][1:])

    # ===== 检查1：A1-A3 =====
    if A < 4:
        print("❌ 错误：推荐了 A1-A3")
        error_A += 1

    # ===== 检查2：必须带B =====
    if "B" not in location:
        print("❌ 错误：没有B位")
        error_B += 1

    # ===== 检查3：是否推荐满位 =====
    subset = df[(df["A"]==A)&(df["R"]==R)&(df["L"]==L)]
    occupied_count = len(subset[subset["status"]=="occupied"])

    if occupied_count >= 3:
        print("❌ 错误：推荐了满B位")
        error_full += 1

    print("-" * 30)

# ==============================
# 📊 汇总结果
# ==============================
print("\n====== 测试结果 ======")
print(f"A区错误: {error_A}")
print(f"B位错误: {error_B}")
print(f"满位错误: {error_full}")
print("======================")