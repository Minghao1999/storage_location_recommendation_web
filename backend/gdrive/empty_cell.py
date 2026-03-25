import requests
import json
from lxml import etree
import pandas as pd

COLUMN_MAPPING = {
    "zoneNo": "储区编码",
    "cellNo": "储位编码",
    "cellType": "储位类型",
    "pickFlag": "拣货区别",
    "cellStatus": "储位状态",
    "skuQty": "商品品数",
    "qty": "总商品件数",
}

COLUMN_ORDER = [
    "储区编码",
    "储位编码",
    "储位类型",
    "拣货区别",
    "储位状态",
    "商品品数",
    "总商品件数",
]

URL = "https://iwms.us.jdlglobal.com/reportApi/services/smartQueryWS?wsdl"

HEADERS = {
    "accept": "application/xml, text/xml, */*; q=0.01",
    "content-type": "text/xml; charset=UTF-8",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJkdXJhdGlvbiI6ODY0MDAsImxvZ2luQWNjb3VudCI6ImpkaGtfa0ZHb1V0bWJOU0tGIiwibG9naW5UaW1lIjoiMjAyNi0wMy0yNSAyMzoxNTo1MCIsIm9yZ05vIjoiMSIsImxvZ2luVHlwZSI6ImIiLCJpc0F1dGhJZ25vcmVkIjpmYWxzZSwidGVuYW50Tm8iOiJBMDAwMDAwMDAzMyIsImxvZ2luQ2xpZW50IjoiUEMiLCJkaXN0cmlidXRlTm8iOiIxIiwid2FyZWhvdXNlTm8iOiJDMDAwMDAwOTk0MyIsInRpbWVzdGFtcCI6MTc3NDQ1MTc1MDY4Mn0.iMpyspQLNS47zfOvO2Fq-mpsp-oCoSt1eGZayCrUitM",
    "routerule": "1,1,C0000009943",
}


def build_body(page):
    arg0 = {
        "bizType": "queryExportByCondition",
        "uuid": "1",
        "callCode": "360BUY.WMS3.WS.CALLCODE.10401"
    }

    arg1 = {
        "Id": "wms_cell_status",
        "Name": "cellStatus",
        "WkNo": "jdhk_kFGoUtmbNSKF",
        "UserName": "wujianghao0706@gmail.com",
        "ReportModelId": "",
        "SqlLimit": "5000",
        "ListSqlOrder": [],
        "ListSqlWhere": [
            {
                "FirstValue": "idle",
                "Compare": 0,
                "FieldId": "cellStatus",
                "FieldName": "storeState",
                "Location": "B"
            }
        ],
        "PageSize": 2000, 
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

def fetch_all():
    all_rows = []
    page = 1

    while True:
        print(f"Fetching page {page}")

        body = build_body(page)

        resp = requests.post(URL, headers=HEADERS, data=body, timeout=60)
        resp.raise_for_status()

        result = parse_response(resp.text)

        if not result:
            break

        data = result.get("data")
        if not data:
            break

        rows = json.loads(data)

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < 1000:
            break

        page += 1

    return all_rows

def parse_response(xml_text):
    root = etree.fromstring(xml_text.encode("utf-8"))
    nodes = root.xpath("//resultValue/text()")

    if not nodes:
        return None

    result = json.loads(nodes[0])

    if isinstance(result, str):
        result = json.loads(result)

    return result


def create_export_task():
    body = build_body()

    resp = requests.post(URL, headers=HEADERS, data=body, timeout=60)
    resp.raise_for_status()

    result = parse_response(resp.text)

    if not result:
        print("创建任务失败")
        return None

    data = result.get("data")

    if not data:
        print("没有数据")
        return None

    rows = json.loads(data)

    return rows


if __name__ == "__main__":
    rows = fetch_all()

    import pandas as pd
    df = pd.DataFrame(rows)

    df = df.rename(columns=COLUMN_MAPPING)

    df = df[COLUMN_ORDER]

    df.to_excel("empty_slots.xlsx", index=False)
    print(f"已导出 {len(df)} 条空储位")