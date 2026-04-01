import time

CACHE = {}
TTL = 3600  # 1小时

def get(key):
    if key in CACHE:
        value, ts = CACHE[key]
        if time.time() - ts < TTL:
            return value
        else:
            del CACHE[key]
    return None

def set(key, value):
    CACHE[key] = (value, time.time())