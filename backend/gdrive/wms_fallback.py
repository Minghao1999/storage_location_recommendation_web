from gdrive.inventory_query import build_body, parse_response, HEADERS, URL
import requests
import json
import time


def query_wms_by_sku(sku):
    """
    通过 WMS 接口查询单个 SKU
    支持：
    - 京东商品编码 goodsNo
    - 客户商品编码 goods_alias_code
    """

    def fetch_with_field(field):
        body = build_body_with_condition(field, sku)

        resp = requests.post(URL, headers=HEADERS, data=body, timeout=30)
        resp.raise_for_status()

        result = parse_response(resp.text)

        # ⭐ 防止 None 报错
        if not result:
            return []

        rows = (
            result.get("data")
            or result.get("rows")
            or result.get("list")
            or result.get("result")
            or []
        )

        if isinstance(rows, str):
            try:
                rows = json.loads(rows)
            except:
                return []

        return rows if isinstance(rows, list) else []

    # ===== 先按京东SKU查 =====
    rows = fetch_with_field("goodsNo")

    if rows:
        return rows

    # ===== 再按客户SKU查 =====
    rows = fetch_with_field("goods_alias_code")
    if rows:
        return rows

    #最后按商品条码查
    rows = fetch_with_field("barcode")

    return rows

    


def build_body_with_condition(field, value):
    arg0 = {
        "bizType": "queryReportByCondition",
        "uuid": "1",
        "callCode": "360BUY.WMS3.WS.CALLCODE.10401"
    }

    where = [{
        "FieldId": field,
        "FieldName": field,
        "Compare": 0,  # =
        "FirstValue": value,
        "Location": "A"
    }]

    arg1 = {
        "Id": "stockReport",
        "Name": "commodityInventoryInformationInquiry",
        "WkNo": "jdhk_kFGoUtmbNSKF",
        "UserName": "wujianghao0706@gmail.com",
        "ReportModelId": "",
        "SqlLimit": "100",
        "ListSqlOrder": [],
        "ListSqlWhere": where,
        "PageSize": 100,
        "CurrentPage": 1,
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