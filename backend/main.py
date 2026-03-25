from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gdrive.gdrive_loader import download_daily_files
from data_loader import load_data
from sku_finder import find_location_by_sku
from datetime import datetime
from sku_finder import find_location_by_size
from logger import log_search, mark_shift

app = FastAPI()

# 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

df = None
inventory_all = None


def refresh_data():
    global df, inventory_all
    inventory_file, empty_file = download_daily_files()
    df, inventory_all = load_data(inventory_file, empty_file)


# 启动时先加载一次
refresh_data()


class SKURequest(BaseModel):
    sku: str

class DriftRequest(BaseModel):
    sku: str
    location: str


@app.get("/")
def home():
    return {"message": "Warehouse Web API is running"}


@app.get("/refresh")
def refresh():
    refresh_data()
    return {"success": True, "message": "Data refreshed"}

@app.post("/drift")
def report_drift(req: DriftRequest):
    sku = req.sku.strip().upper()
    location = req.location

    updated = mark_shift(sku, location)

    if updated:
        return {
            "success": True,
            "message": f"Shift marked: {location}"
        }

    return {
        "success": False,
        "message": "Matching search record not found"
    }


@app.post("/search")
@app.post("/search")
def search_sku(req: SKURequest):
    global df, inventory_all

    sku = req.sku.strip().upper()

    if not sku:
        return {
            "success": False,
            "message": "SKU is empty"
        }

    location, item_len, space = find_location_by_sku(df, inventory_all, sku)

    # ===== 有推荐 =====
    if location:
        try:
            parts = location.split("-")
            A = int(parts[0].replace("A",""))
            R = int(parts[1].replace("R",""))
            L = int(parts[2].replace("L",""))
            B = int(parts[3].replace("B",""))
        except:
            return {"success": False, "message": "Invalid location format"}

        # ✅ 先定义
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

        # ✅ 再使用
        df.loc[len(df)] = new_row

        # ✅ 只记录一次
        log_search(
            sku=sku,
            location=location,
            item_len=item_len,
            space=space,
            success=True
        )

        return {
            "success": True,
            "sku": sku,
            "location": location,
            "length": item_len,
            "remaining": space
        }

    # ===== SKU不存在 =====
    if item_len is None:
        log_search(
            sku=sku,
            location=None,
            item_len=None,
            space=None,
            success=False
        )
        return {
            "success": False,
            "sku": sku,
            "message": "SKU not found in database"
        }

    # ===== 没有库位 =====
    log_search(
        sku=sku,
        location=location,
        item_len=item_len,
        space=space,
        success=False
    )

    return {
        "success": False,
        "sku": sku,
        "length": item_len,
        "message": "No available location"
    }

putaway_log = []   # 简单先用内存（后面可以换数据库）


class ConfirmRequest(BaseModel):
    sku: str
    location: str
    length: float


@app.post("/confirm")
def confirm_putaway(req: ConfirmRequest):
    global df

    sku = req.sku.strip().upper()
    location = req.location

    try:
        parts = location.split("-")
        A = int(parts[0].replace("A",""))
        R = int(parts[1].replace("R",""))
        L = int(parts[2].replace("L",""))
        B = int(parts[3].replace("B","")) 
    except:
        return {"success": False, "message": "Invalid location format"}

    # ===== 写入 df（模拟上架）=====
    new_row = {
        "A": A,
        "R": R,
        "L": L,
        "B": B,
        "长": req.length,
        "宽": 0,
        "高": 0,
        "status": "occupied",
        "SKU_ALL": sku
    }

    df.loc[len(df)] = new_row


    return {
        "success": True,
        "message": f"Putaway success: {location}"
    }

class SizeRequest(BaseModel):
    length: float
    width: float
    height: float


@app.post("/search_by_size")
def search_by_size(req: SizeRequest):
    global df

    item_len = max(req.length, req.width, req.height)

    location, item_len, space = find_location_by_size(df, item_len)

    if location:
        return {
            "success": True,
            "location": location,
            "length": item_len,
            "remaining": space
        }

    return {
        "success": False,
        "message": "No available location"
    }