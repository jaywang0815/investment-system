"""
客戶姓名比對 - 解決 開戶 用全名、SN sheet 用遮罩名 (黃＊維) 造成重複客戶的問題

masked name 規則:
  黃＊維 / 黃*維  → 黃 + 任意字 + 維   (＊ 或 * = 萬用字元)
  翁＊            → 翁 + 任意字

回傳的 status:
  exact     完全相同
  masked    遮罩名只對到「一個」全名 → 可安心連結
  ambiguous 遮罩名對到「多個」全名 → 需人工選擇
  nickname  非遮罩、非全名 (例如 游爸/秦/莫姐) → 需人工對應
  none      候選清單為空
"""
import re
import unicodedata
from typing import Optional


def _norm(name: str) -> str:
    return unicodedata.normalize("NFKC", str(name)).strip()


def is_masked(name: str) -> bool:
    return "*" in _norm(name)


def match_customer(name: str, candidates: list) -> dict:
    """
    name        : SN sheet 的客戶名 (可能是全名/遮罩名/暱稱)
    candidates  : 既有客戶全名清單 (開戶 的官方姓名)
    回傳        : {"match": <全名 or None>, "status": <see module doc>, "options": [..]}
    """
    n = _norm(name)
    cands = [_norm(c) for c in candidates]

    # 1) 完全相同
    if n in cands:
        return {"match": n, "status": "exact", "options": [n]}

    # 2) 遮罩名 → 萬用字元比對
    if is_masked(n):
        # 每個 * 視為 1 個以上的任意字 (中文姓名遮罩通常遮 1 字)
        pattern = "^" + re.escape(n).replace(r"\*", ".+") + "$"
        # re.escape 會把 * 轉成 \* ; 上面已還原為 .+
        rx = re.compile(pattern)
        hits = [c for c in cands if rx.match(c)]
        if len(hits) == 1:
            return {"match": hits[0], "status": "masked", "options": hits}
        if len(hits) > 1:
            return {"match": None, "status": "ambiguous", "options": hits}
        return {"match": None, "status": "nickname", "options": []}

    # 3) 非遮罩、非全名 → 暱稱 (游爸/秦/莫姐...) 無法自動對應
    #    嘗試「同姓氏」給人工參考
    same_surname = [c for c in cands if c and n and c[0] == n[0]]
    return {"match": None, "status": "nickname", "options": same_surname}
