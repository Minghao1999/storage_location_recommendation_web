import requests
import os
from datetime import date


def download_file(file_id, output):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"

    r = requests.get(url)

    if r.status_code != 200:
        raise Exception("Download failed")

    with open(output, "wb") as f:
        f.write(r.content)


def download_daily_files():
    inventory_id = "1Upbjv3sonyg40F9Rk1wTp7IltCK4ROB-"
    empty_id = "1NV_g66yMuLzttr2X7fvx71oMjTpPlQ2d"

    os.makedirs("gdrive/data", exist_ok=True)

    today = date.today().strftime("%Y-%m-%d")

    inventory_path = f"gdrive/data/inventory_{today}.xlsx"
    empty_path = f"gdrive/data/empty_{today}.xlsx"

    if not os.path.exists(inventory_path):
        download_file(inventory_id, inventory_path)

    if not os.path.exists(empty_path):
        download_file(empty_id, empty_path)

    return inventory_path, empty_path