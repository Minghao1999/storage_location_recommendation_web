from db_helper import get_sku_info
import pandas as pd

MIN_A = 4

import math

PALLET_SIZE = 40

INVALID_SLOTS = {
    (4, 4),
    (4, 6)
}

def is_valid_slot(A, R):
    return (A, R) not in INVALID_SLOTS

def can_fit_pallet(space, item_len):
    required = math.ceil(item_len / PALLET_SIZE)
    available = int(space // PALLET_SIZE)
    return available >= required

def get_slot_capacity(R):
    if R in [19, 20, 23, 24]:
        return 80
    return 120

def is_fully_empty(df, A, R, L):
    subset = df[
        (df["A"] == A) &
        (df["R"] == R) &
        (df["L"] == L)
    ]

    return not any(subset["status"] == "occupied")


def get_remaining_space(df):
    occupied = df[df["status"] == "occupied"].copy()

    for col in ["长", "宽", "高"]:
        occupied[col] = pd.to_numeric(occupied[col], errors="coerce").fillna(0)

    occupied["占用长度"] = occupied[["长", "宽", "高"]].max(axis=1)

    used = (
        occupied
        .groupby(["A", "R", "L"], as_index=False)["占用长度"]
        .sum()
    )

    used_dict = {
        (row["A"], row["R"], row["L"]): row["占用长度"]
        for _, row in used.iterrows()
    }

    remaining = {}

    all_slots = df.groupby(["A", "R", "L"]).size().index

    for slot in all_slots:
        A, R, L = slot
        capacity = get_slot_capacity(R)
        used_len = used_dict.get(slot, 0)
        remaining[slot] = max(0, capacity - used_len)

    return remaining


def find_available_B(df, A, R, L, item_len=None):
    if item_len is not None and item_len > 120:
        if is_fully_empty(df, A, R, L):
            return 1  # 直接放 B1
        else:
            return None
        
    subset = df[
        (df["A"] == A) &
        (df["R"] == R) &
        (df["L"] == L)
    ]

    occupied_B = set(
        subset[subset["status"] == "occupied"]["B"].dropna().astype(int)
    )

    all_B = {1, 2, 3}
    empty_B = all_B - occupied_B

    # 优先 B1 -> B3 -> B2
    for b in [1, 3, 2]:
        if b in empty_B:
            return b

    return None


def find_location_by_size(df, item_len):
    remaining = get_remaining_space(df)

    # 先按 L1 优先，再 L2/L3/L4
    target_levels = [1, 2, 3, 4]

    for level in target_levels:
        candidates = {
            k: v for k, v in remaining.items()
            if k[2] == level
            and k[0] >= MIN_A
            and is_valid_slot(k[0], k[1])
            and (
                # ⭐ 普通货
                (item_len <= 120 and can_fit_pallet(v, item_len))
                
                # ⭐ 超长货
                or (item_len > 120 and is_fully_empty(df, k[0], k[1], k[2]))
            )
            and find_available_B(df, k[0], k[1], k[2], item_len) is not None
        }

        if candidates:
            best = min(candidates, key=candidates.get)
            A, R, L = best
            B = find_available_B(df, A, R, L, item_len)
            return f"A{A}-R{R}-L{L}-B{B}", item_len, candidates[best]

    return None, item_len, None


def find_location_by_sku(df, inventory_all, sku):
    sku = sku.strip().upper()

    sku_info = get_sku_info(sku)
    if sku_info is None:
        return None, None, None

    item_len = sku_info["最长边"]
    remaining = get_remaining_space(df)

    all_slots = set(remaining.keys())

    occupied_slots = set(
        df[df["status"] == "occupied"]
        .groupby(["A", "R", "L"])
        .size()
        .index
    )

    empty_slots = all_slots - occupied_slots

    sku_locations = df[
        (df["CLIENT_SKU"] == sku) |
        (df["JD_SKU"] == sku)
    ]
    L1_has_sku = any(sku_locations["L"] == 1)

    if L1_has_sku:
        target_levels = [2, 3, 4]
    else:
        target_levels = [1]

    # 1) 先找已有货储位
    for level in target_levels:
        candidates = {
            k: v for k, v in remaining.items()
            if k in occupied_slots
            and k[2] == level
            and k[0] >= MIN_A
            and is_valid_slot(k[0], k[1])
            and (
                # ⭐ 普通货
                (item_len <= 120 and can_fit_pallet(v, item_len))
                
                # ⭐ 超长货
                or (item_len > 120 and is_fully_empty(df, k[0], k[1], k[2]))
            )
            and find_available_B(df, k[0], k[1], k[2], item_len) is not None
        }

        if candidates:
            best = min(candidates, key=candidates.get)
            A, R, L = best
            B = find_available_B(df, A, R, L, item_len)
            return f"A{A}-R{R}-L{L}-B{B}", item_len, candidates[best]

    # 2) 再找完全空储位
    for level in target_levels:
        candidates = {
            k: v for k, v in remaining.items()
            if k in empty_slots
            and k[2] == level
            and k[0] >= MIN_A
            and is_valid_slot(k[0], k[1])
            and (
                # ⭐ 普通货
                (item_len <= 120 and can_fit_pallet(v, item_len))
                
                # ⭐ 超长货
                or (item_len > 120 and is_fully_empty(df, k[0], k[1], k[2]))
            )
            and find_available_B(df, k[0], k[1], k[2], item_len) is not None
        }

        if candidates:
            best = min(candidates, key=candidates.get)
            A, R, L = best
            B = find_available_B(df, A, R, L, item_len)
            return f"A{A}-R{R}-L{L}-B{B}", item_len, candidates[best]

    # 3) 兜底：跨层
    for level in [1, 2, 3, 4]:
        candidates = {
            k: v for k, v in remaining.items()
            if k[2] == level
            and k[0] >= MIN_A
            and is_valid_slot(k[0], k[1])
            and (
                # ⭐ 普通货
                (item_len <= 120 and can_fit_pallet(v, item_len))
                
                # ⭐ 超长货
                or (item_len > 120 and is_fully_empty(df, k[0], k[1], k[2]))
            )
            and find_available_B(df, k[0], k[1], k[2], item_len) is not None
        }

        if candidates:
            best = min(candidates, key=candidates.get)
            A, R, L = best
            B = find_available_B(df, A, R, L, item_len)
            return f"A{A}-R{R}-L{L}-B{B}", item_len, candidates[best]

    return None, item_len, None