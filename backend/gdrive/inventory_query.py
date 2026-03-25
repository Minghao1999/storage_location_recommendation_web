import requests
import json
import pandas as pd
from lxml import etree
import time
import random

URL = "https://iwms.us.jdlglobal.com/reportApi/services/smartQueryWS?wsdl"

HEADERS = {
    "accept": "application/xml, text/xml, */*; q=0.01",
    "content-type": "text/xml; charset=UTF-8",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJkdXJhdGlvbiI6ODY0MDAsImxvZ2luQWNjb3VudCI6ImpkaGtfa0ZHb1V0bWJOU0tGIiwibG9naW5UaW1lIjoiMjAyNi0wMy0yNSAyMjoxNTo0NCIsIm9yZ05vIjoiMSIsImxvZ2luVHlwZSI6ImIiLCJpc0F1dGhJZ25vcmVkIjpmYWxzZSwidGVuYW50Tm8iOiJBMDAwMDAwMDAzMyIsImxvZ2luQ2xpZW50IjoiUEMiLCJkaXN0cmlidXRlTm8iOiIxIiwid2FyZWhvdXNlTm8iOiJDMDAwMDAwOTk0MyIsInRpbWVzdGFtcCI6MTc3NDQ0ODE0NDExNX0.EzgsEFFoO8f4_qbCqyUnQznx9KgGcVBrna7NB66KCaM", 
    "routerule": "1,1,C0000009943",
}

PAGE_SIZE = 2000

COLUMN_MAPPING = {
    "goodsNo": "京东商品编码",
    "barcode": "商品条码",
    "goods_alias_code": "客户商品编码",
    "goodsName": "商品名称",
    "productLevelNameAlias": "商品等级",

    "length": "长",
    "width": "宽",
    "height": "高",
    "weight": "重量",

    "ownerNo": "货主编号",
    "ownerName": "货主名称",
    "customerCode": "客户编码",

    "cellNo": "储位编码",
    "zoneNo": "储区号",
    "zoneName": "储区名称",
    "zoneType": "储区类型",

    "lotNo": "批次号",
    "packageBatch": "包装批号",

    "cellQty": "库存量",
    "activeQty": "可用量",
    "nonsalesQty": "不可用量",
    "prepickedQty": "订单预占量",
    "premovedQty": "移库预占量",
    "vasOccupyQty": "VAS预占量",
    "lockedQty": "总锁定量",

    "inboundDate": "入库日期",
    "prodDate": "生产日期",
    "expdDate": "到期日期",

    "lpnCode": "LPN",
    "saleUnit": "计量单位",
}

COLUMN_ORDER = [
    "京东商品编码",
    "商品条码",
    "客户商品编码",
    "商品名称",
    "商品等级",
    "长", "宽", "高", "重量",
    "货主编号", "货主名称", "客户编码",
    "储位编码",
    "批次号",
    "库存量", "可用量", "不可用量",
    "订单预占量", "移库预占量", "VAS预占量",
    "总锁定量",
    "LPN",
    "计量单位",
    "储区号", "储区名称", "储区类型",
    "入库日期",
    "生产日期",
    "到期日期",
]


def build_body(page):
    arg0 = {
        "bizType": "queryReportByCondition",
        "uuid": "1",
        "callCode": "360BUY.WMS3.WS.CALLCODE.10401"
    }

    arg1 = {
        "Id": "stockReport",
        "Name": "commodityInventoryInformationInquiry",
        "WkNo": "jdhk_kFGoUtmbNSKF",          
        "UserName": "wujianghao0706@gmail.com",
        "ReportModelId": "",
        "SqlLimit": "5000",
        "ListSqlOrder": [],
        "ListSqlWhere": [],
        "PageSize": PAGE_SIZE,
        "CurrentPage": page,
        "orgNo": "1",
        "distributeNo": "1",
        "warehouseNo": "C0000009943"
    }

    soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <wms3:queryWs xmlns:wms3="http://wms3.360buy.com">
      <arg0>{json.dumps(arg0)}</arg0>
      <arg1>{json.dumps(arg1)}</arg1>
    </wms3:queryWs>
  </soap:Body>
</soap:Envelope>
"""
    return soap


def parse_response(xml_text):
    root = etree.fromstring(xml_text.encode("utf-8"))
    nodes = root.xpath("//resultValue/text()")

    if not nodes:
        return None

    return json.loads(nodes[0])


def fetch_all():
    all_rows = []
    page = 1

    while True:
        print(f"Fetching page {page}")

        body = build_body(page)
        resp = requests.post(URL, headers=HEADERS, data=body, timeout=60)

        time.sleep(random.uniform(1, 2))
        resp.raise_for_status()

        result = parse_response(resp.text)

        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                break

        if not result:
            break

        rows = (
            result.get("data")
            or result.get("rows")
            or result.get("list")
            or result.get("result")
            or []
        )

        # 处理 rows 可能是字符串
        if isinstance(rows, str):
            try:
                rows = json.loads(rows)
            except:
                break

        # 处理 rows 里是字符串
        if isinstance(rows, list) and len(rows) > 0 and isinstance(rows[0], str):
            try:
                rows = [json.loads(x) if isinstance(x, str) else x for x in rows]
            except:
                break

        if not rows:
            break

        if isinstance(rows, list):
            all_rows.extend(rows)
        elif isinstance(rows, dict):
            all_rows.append(rows)
        else:
            break

        if len(rows) < PAGE_SIZE:
            print("Last page.")
            break

        page += 1

    return all_rows


def export_excel(data, filename):
    df = pd.DataFrame(data)

    # 字段映射
    df = df.rename(columns=COLUMN_MAPPING)

    # 补列
    for col in COLUMN_ORDER:
        if col not in df.columns:
            df[col] = ""

    # 排序
    df = df[COLUMN_ORDER]

    # ⭐ 导出 Excel
    df.to_excel(filename, index=False)

    print(f"Exported {len(df)} rows")


if __name__ == "__main__":
    data = fetch_all()
    export_excel(data, "inventory_report.xlsx")