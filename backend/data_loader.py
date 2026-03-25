import pandas as pd


def load_data(inventory_path, empty_path):
    inventory = pd.read_excel(inventory_path)

    inventory["长"] = pd.to_numeric(inventory.iloc[:, 6], errors="coerce")

    # 客户SKU（C列）
    inventory["CLIENT_SKU"] = (
        inventory.iloc[:, 2]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    inventory["JD_SKU"] = (
        inventory.iloc[:,0]
        .astype(str)
        .str.strip()
        .str.upper()
    )
    
    inventory["SKU_LIST"] = inventory.apply(
        lambda row: [row["CLIENT_SKU"], row["JD_SKU"]],
        axis=1
    )

    # 保存完整库存（用于SKU查询）
    inventory_all = inventory.copy()

    empty = pd.read_excel(empty_path)
    empty["长"] = 0

    # 只筛选 A1-A24 给推荐逻辑
    inventory_loc = inventory.iloc[:, 15].astype(str)
    inventory_A = pd.to_numeric(inventory_loc.str.extract(r"A(\d+)")[0], errors="coerce")
    inventory_A24 = inventory[inventory_A.between(1, 24)].copy()

    inventory_A24["SKU_ALL"] = inventory_A24["CLIENT_SKU"]

    empty_loc = empty["储位编码"].astype(str)
    empty_A = pd.to_numeric(empty_loc.str.extract(r"A(\d+)")[0], errors="coerce")
    empty = empty[empty_A.between(1, 24)].copy()

    inventory_A24["status"] = "occupied"
    empty["status"] = "empty"

    df = pd.concat([inventory_A24, empty], ignore_index=True)

    loc = df["储位编码"].astype(str)

    df["A"] = pd.to_numeric(loc.str.extract(r"A(\d+)")[0], errors="coerce")
    df["R"] = pd.to_numeric(loc.str.extract(r"R(\d+)")[0], errors="coerce")
    df["L"] = pd.to_numeric(loc.str.extract(r"L(\d+)")[0], errors="coerce")
    df["B"] = pd.to_numeric(loc.str.extract(r"B(\d+)")[0], errors="coerce")

    df = df.dropna(subset=["A", "R", "L"])
    df = df[df["L"] != 5]

    return df, inventory_all