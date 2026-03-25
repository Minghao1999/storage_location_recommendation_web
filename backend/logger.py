from datetime import datetime
import os

LOG_FILE = "log.csv"


def ensure_log_file():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("time,sku,location,item_len,space,success,shift\n")


def log_search(sku, location=None, item_len=None, space=None, success=True):
    ensure_log_file()

    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line = (
        f"{time_str},"
        f"{sku},"
        f"{location},"
        f"{item_len},"
        f"{space},"
        f"{success},"
        f"\n"
    )

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def mark_shift(sku, location):
    ensure_log_file()

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) <= 1:
        return False

    header = lines[0]
    rows = lines[1:]

    for i in range(len(rows) - 1, -1, -1):
        parts = rows[i].rstrip("\n").split(",")

        while len(parts) < 7:
            parts.append("")

        row_time, row_sku, row_location, item_len, space, success, shift = parts

        if row_sku == sku and row_location == location:
            parts[6] = "TRUE"
            rows[i] = ",".join(parts) + "\n"
            break
    else:
        return False

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(header)
        f.writelines(rows)

    return True