from datetime import date
import os

from gdrive.inventory_query import fetch_all as fetch_inventory, export_excel
from gdrive.empty_cell import fetch_all as fetch_empty, COLUMN_MAPPING, COLUMN_ORDER


def download_daily_files():
    os.makedirs("gdrive/data", exist_ok=True)

    today = date.today().strftime("%Y-%m-%d")

    inventory_path = f"gdrive/data/inventory_{today}.xlsx"
    empty_path = f"gdrive/data/empty_{today}.xlsx"

    # ===== 拉 inventory =====
    if not os.path.exists(inventory_path):
        print("Fetching inventory from API...")
        data = fetch_inventory()
        export_excel(data, inventory_path)

    # ===== 拉 empty =====
    if not os.path.exists(empty_path):
        print("Fetching empty slots from API...")
        rows = fetch_empty()

        import pandas as pd

        df = pd.DataFrame(rows)
        df = df.rename(columns=COLUMN_MAPPING)

        for col in COLUMN_ORDER:
            if col not in df.columns:
                df[col] = ""

        df = df[COLUMN_ORDER]
        df.to_excel(empty_path, index=False)

    return inventory_path, empty_path