import pandas as pd

def load_data(inventory_path, empty_path):
    inventory = pd.read_excel(inventory_path)

    inventory["长"] = pd.to_numeric(inventory["长"], errors="coerce")
    inventory["宽"] = pd.to_numeric(inventory["宽"], errors="coerce")
    inventory["高"] = pd.to_numeric(inventory["高"], errors="coerce")

    inventory["CLIENT_SKU"] = inventory["客户商品编码"].astype(str).str.strip().str.upper()
    inventory["JD_SKU"] = inventory["京东商品编码"].astype(str).str.strip().str.upper()
    
    inventory["SKU_LIST"] = inventory.apply(
        lambda row: [row["CLIENT_SKU"], row["JD_SKU"]],
        axis=1
    )

    # 保存完整库存（用于SKU查询）
    inventory_all = inventory.copy()

    empty = pd.read_excel(empty_path)
    empty["长"] = 0
    empty["宽"] = 0
    empty["高"] = 0

    # 2. 直接提取正确的 "储位编码" 列
    inventory_loc = inventory["储位编码"].astype(str)
    inventory_A = pd.to_numeric(inventory_loc.str.extract(r"A(\d+)")[0], errors="coerce")
    inventory_A24 = inventory[inventory_A.between(1, 24)].copy()

    inventory_A24["SKU_ALL"] = inventory_A24["CLIENT_SKU"]
    inventory_A24["status"] = "occupied"

    # 处理空储位表
    empty_loc = empty["储位编码"].astype(str)
    empty_A = pd.to_numeric(empty_loc.str.extract(r"A(\d+)")[0], errors="coerce")
    empty = empty[empty_A.between(1, 24)].copy()
    empty["status"] = "empty"

    # 3. 合并数据（两边都有 "储位编码" 这一列，concat 会完美对齐）
    df = pd.concat([inventory_A24, empty], ignore_index=True)

    # 4. 解析 A, R, L, B 坐标
    loc = df["储位编码"].astype(str)
    df["A"] = pd.to_numeric(loc.str.extract(r"A(\d+)")[0], errors="coerce")
    df["R"] = pd.to_numeric(loc.str.extract(r"R(\d+)")[0], errors="coerce")
    df["L"] = pd.to_numeric(loc.str.extract(r"L(\d+)")[0], errors="coerce")
    
    # 兼容尾部托盘位：匹配 B1 或 -1
    df["B"] = pd.to_numeric(loc.str.extract(r"(?:B|-)(\d+)$")[0], errors="coerce")

    # 清洗掉解析失败的垃圾数据
    df = df.dropna(subset=["A", "R", "L"])

    return df, inventory_all