from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gdrive.gdrive_loader import download_daily_files, download_daily_files_safe
from data_loader import load_data
from sku_finder import find_location_by_sku
from datetime import datetime
from sku_finder import find_location_by_size
from logger import log_search, mark_shift
from gdrive.wms_fallback import query_wms_by_sku
import threading
from time import time

app = FastAPI()

lock = threading.Lock()
is_refreshing = False

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

refresh_status = "idle"

@app.get("/refresh_status")
def get_status():
    return {"status": refresh_status}

def init_data():
    global df, inventory_all
    inventory_file, empty_file = download_daily_files()
    df, inventory_all = load_data(inventory_file, empty_file)

# 启动时执行
init_data()

class SKURequest(BaseModel):
    sku: str

class DriftRequest(BaseModel):
    sku: str
    location: str


@app.get("/")
def home():
    return {"message": "Warehouse Web API is running"}

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

last_refresh_time = 0
REFRESH_COOLDOWN = 100  
@app.get("/refresh")
def refresh():
    global is_refreshing, refresh_status, last_refresh_time

    now = time()

    # 🚫 1. 冷却限制
    if now - last_refresh_time < REFRESH_COOLDOWN:
        return {
            "success": False,
            "message": "Too frequent. Please wait."
        }

    # 🚫 2. 正在刷新
    if is_refreshing:
        return {
            "success": False,
            "message": "Already refreshing"
        }

    last_refresh_time = now
    is_refreshing = True

    def task():
        global is_refreshing
        try:
            refresh_data_async()
        finally:
            is_refreshing = False

    threading.Thread(target=task, daemon=True).start()

    return {
        "success": True,
        "message": "Refresh started"
    }

def refresh_data_async():
    global df, inventory_all, refresh_status

    try:
        refresh_status = "running"   # ✅ 开始

        inventory_file, empty_file = download_daily_files_safe()
        new_df, new_inventory = load_data(inventory_file, empty_file)

        with lock:
            df = new_df
            inventory_all = new_inventory

        refresh_status = "done"   # ✅ 完成
        print("Data hot-swapped successfully")

    except Exception as e:
        refresh_status = "error"  # ✅ 出错
        print("Refresh failed:", e)

@app.post("/search")
def search_sku(req: SKURequest):
    global df, inventory_all

    sku = req.sku.strip().upper()

    if not sku:
        return {
            "success": False,
            "message": "SKU is empty"
        }
    with lock:
        local_df = df
        local_inventory = inventory_all

    # 在锁外计算
    location, item_len, space = find_location_by_sku(local_df, local_inventory, sku)
    # ================== 新增：从总表中提取商品条码 ==================
    barcode = ""
    if local_inventory is not None and "SKU_LIST" in local_inventory.columns:
        match_row = local_inventory[
            local_inventory["SKU_LIST"].apply(lambda lst: sku in lst if isinstance(lst, list) else False)
        ]
        if not match_row.empty and "BARCODE" in match_row.columns:
            # 提取条码并进行清洗
            b_val = str(match_row.iloc[0]["BARCODE"]).strip()
            if b_val.upper() not in ["NAN", "NONE", ""]:
                barcode = b_val
    # ===============================================================

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
        with lock:
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
            "remaining": space,
            "barcode": barcode  # 👉 这里把 barcode 发给前端！
        }

    # ===== SKU不存在（本地没找到）=====
    if item_len is None:

        print("Local DB miss → querying WMS...")

        rows = query_wms_by_sku(sku)

        # ===== WMS 找到了 =====
        if rows:
            wms_barcode = barcode
            if not wms_barcode and len(rows) > 0:
                wms_barcode = rows[0].get("barcode", "")
                
            # 👉 1. 从 WMS 数据中提取长、宽、高 (如果为空则默认为 0)
            w_len = float(rows[0].get("length", 0) or 0)
            w_wid = float(rows[0].get("width", 0) or 0)
            w_hei = float(rows[0].get("height", 0) or 0)
            
            # 算出最长边作为 item_len
            wms_item_len = max(w_len, w_wid, w_hei)

            # 👉 2. 拿着 WMS 给的尺寸，去调用你的“按尺寸推荐储位”函数！
            rec_location, final_len, space = find_location_by_size(df, wms_item_len)

            # 如果仓库满了，算不出推荐储位
            if not rec_location:
                log_search(sku=sku, location=None, item_len=wms_item_len, space=None, success=False)
                return {
                    "success": False,
                    "sku": sku,
                    "length": wms_item_len,
                    "barcode": wms_barcode,
                    "message": "Found dimensions in WMS, but warehouse is full!"
                }

            # 👉 3. 成功算出了新储位，把它写入 df 锁定，防止重复推荐
            try:
                parts = rec_location.split("-")
                A = int(parts[0].replace("A",""))
                R = int(parts[1].replace("R",""))
                L = int(parts[2].replace("L",""))
                B = int(parts[3].replace("B",""))
                with lock:
                    df.loc[len(df)] = {
                        "A": A, "R": R, "L": L, "B": B,
                        "长": final_len, "宽": 0, "高": 0,
                        "status": "occupied", "SKU_ALL": sku
                    }
            except:
                pass # 解析失败忽略

            # 记录成功日志
            log_search(sku=sku, location=rec_location, item_len=final_len, space=space, success=True)

            # 👉 4. 把算出来的“全新推荐储位”发给前端
            return {
                "success": True,
                "sku": sku,
                "barcode": wms_barcode,  
                "location": rec_location,   # 这里现在是系统推荐的储位，不再是 WMS 原有储位了！
                "length": final_len,       
                "remaining": space,  
                "message": "Found in WMS and Recommended new location",
                "data": rows[:5]   
            }

        # ===== WMS 也没有 =====
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
            "message": "WMS has not yet entered information."
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
        "barcode": barcode,  # 👉 即使没库位也发回条码
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
    with lock:
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