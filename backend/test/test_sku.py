import sys
import os
import random
import pandas as pd

# ==============================
# 🚀 0. 强行修复 Python 导入路径
# ==============================
# 获取当前脚本所在目录的上一级目录（也就是根目录 Warehouse AUTO WEB）
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# 现在可以安全导入根目录的模块了
from sku_finder import find_location_by_sku
from data_loader import load_data

# ==============================
# 📁 1. 自动找到最新的 inventory 文件
# ==============================
data_dir = os.path.join(BASE_DIR, "gdrive", "data")

try:
    files = [f for f in os.listdir(data_dir) if "inventory" in f]
    empty_files = [f for f in os.listdir(data_dir) if "empty" in f]
    
    if not files or not empty_files:
        raise FileNotFoundError("❌ 数据文件夹中缺少 inventory 或 empty 文件！")

    latest_inventory = sorted(files)[-1]
    inventory_path = os.path.join(data_dir, latest_inventory)

    latest_empty = sorted(empty_files)[-1]
    empty_path = os.path.join(data_dir, latest_empty)

    print("✅ 使用数据文件:")
    print(f"   📦 Inventory: {latest_inventory}")
    print(f"   🕳️ Empty: {latest_empty}\n")

except Exception as e:
    print(e)
    sys.exit(1)

# ==============================
# 📊 2. 加载数据
# ==============================
print("⏳ 正在加载并解析仓库数据...")
df, inventory_all = load_data(inventory_path, empty_path)
print(f"✅ 数据加载完成！当前有效储位记录数: {len(df)}\n")

# ==============================
# 🎯 3. 提取真实 SKU 建立测试池
# ==============================
# 直接用 pandas 按列名或索引读取
inventory_raw = pd.read_excel(inventory_path)
client_sku = inventory_raw["客户商品编码"].astype(str).str.strip().str.upper()
jd_sku = inventory_raw["京东商品编码"].astype(str).str.strip().str.upper()

# 只要 FG 开头的标准 SKU
jd_sku = jd_sku[jd_sku.str.startswith("FG")]
sku_list = pd.concat([client_sku, jd_sku])

# 清洗去重
sku_list = sku_list[(sku_list != "") & (sku_list != "NAN") & (sku_list != "NONE")]
sku_list = sku_list.dropna().unique()

# 随机抽 100 个进行压力测试
sample_size = min(100, len(sku_list))
test_skus = random.sample(list(sku_list), sample_size)
print(f"🎲 随机抽取 {sample_size} 个有效 SKU 进行测试模拟\n")
print("=" * 60)

# ==============================
# 🧪 4. 开始模拟推荐与上架
# ==============================
error_A = 0
error_full = 0
error_B_collision = 0

for i, sku in enumerate(test_skus, 1):
    print(f"[{i}/{sample_size}] 🔍 测试 SKU: '{sku}'")

    # 调用你的核心推荐算法
    location, item_len, space = find_location_by_sku(df, inventory_all, sku)

    if not location:
        print("   ⚠️ 无推荐位置 (库位可能已满或数据库无尺寸)")
        print("-" * 60)
        continue

    # 解析推荐出的坐标
    try:
        parts = location.split("-")
        A_val = int(parts[0].replace("A", ""))
        R_val = int(parts[1].replace("R", ""))
        L_val = int(parts[2].replace("L", ""))
        B_val = int(parts[3].replace("B", "")) 
    except Exception as e:
        print(f"   ❌ [错误] 推荐的储位格式解析失败: {location}")
        print("-" * 60)
        continue

    # 检查推荐的这个大储位（单元格）目前的占用状态
    cell_occupied = df[
        (df["A"] == A_val) & (df["R"] == R_val) & (df["L"] == L_val) & (df["status"] == "occupied")
    ]
    occupied_count = len(cell_occupied)
    existing_skus = cell_occupied["SKU_ALL"].tolist()
    existing_Bs = cell_occupied["B"].dropna().astype(int).tolist()

    print(f"   ✅ 推荐库位: {location} (货物长: {item_len})")
    print(f"   📊 单元格 {A_val}-{R_val}-{L_val} 现状: 已有 {occupied_count} 个托盘")
    if occupied_count > 0:
        print(f"      📦 内部已有 SKU: {existing_skus}")
        print(f"      🔢 已被占用的 B 位: {existing_Bs}")

    # ================= 逻辑校验 =================
    # 1. 检查是否推到了已经有货的 B 位 (碰撞)
    if B_val in existing_Bs:
        print(f"   ❌ [严重错误] 推荐的 B{B_val} 位物理上已经有货了！发生碰撞！")
        error_B_collision += 1

    # 2. 检查满位错误 (假设一个储位最多放3个托盘，按你的业务逻辑调整)
    if occupied_count >= 3:
        print(f"   ❌ [错误] 单元格已满，不应继续推荐！")
        error_full += 1
    
    # 3. 检查 A 区限制 (比如 A1-A3 不推荐)
    if A_val < 4:
        print(f"   ❌ [错误] 违规推荐了 A{A_val} 区域！")
        error_A += 1

    # ================= 模拟上架 =================
    # 将推荐成功的数据写入 df，模拟实际放货。
    # 这样下一个 SKU 测试时，就能感知到这个储位被占用了。
    new_row = {
        "A": A_val, "R": R_val, "L": L_val, "B": B_val,
        "长": item_len, "宽": 0, "高": 0,
        "status": "occupied", "SKU_ALL": sku
    }
    # 使用 pd.concat 替代 df.loc[len(df)] 避免 Pandas 未来版本的警告
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    print("-" * 60)

# ==============================
# 📊 5. 汇总结果
# ==============================
print("\n" + "=" * 20 + " 🏁 测试结果汇总 " + "=" * 20)
print(f"🔴 A区违规推荐: {error_A} 次")
print(f"🔴 储位满载溢出: {error_full} 次")
print(f"🔴 B位重叠碰撞: {error_B_collision} 次")
if error_A == 0 and error_full == 0 and error_B_collision == 0:
    print("🎉 完美！所有逻辑测试通过，没有发生重叠或违规推荐！")
print("=" * 56)