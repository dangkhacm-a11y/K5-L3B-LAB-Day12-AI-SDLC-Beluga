"""File kho v1.0 (Contract G): {"items": {id: số nguyên >= 0}}.

Đọc: từ chối sai schema / id lạ / số âm (BadInput -> mã 2).
Ghi: bỏ mục bằng 0, qua file tạm cùng thư mục rồi thay thế, byte-ổn-định.
"""

import json
import os
import tempfile

from .errors import BadInput

KINDS_P1 = ("ca_loc", "ca_linh", "ca_keo", "bong_dien_dien", "bong_sung", "keo_neo")


def validate_items(items, kinds=KINDS_P1):
    if not isinstance(items, dict):
        raise BadInput("items phải là object")
    out = {}
    for k, v in items.items():
        if k not in kinds:
            raise BadInput(f"nguyên liệu lạ: {k}")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise BadInput(f"số lượng không hợp lệ cho {k}: {v!r}")
        if v > 0:
            out[k] = v
    return out


def read_inventory(path: str, kinds=KINDS_P1):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    if isinstance(data["items"], list):
        # Format v1.2 cá thể
        seen_ids = set()
        for it in data["items"]:
            if not isinstance(it, dict) or "id" not in it or "kind" not in it or "fresh" not in it:
                raise BadInput("item cá thể phải có đủ id, kind, fresh")
            if not it["id"] or it["id"] in seen_ids:
                raise BadInput(f"id trùng hoặc rỗng: {it['id']}")
            seen_ids.add(it["id"])
            if it["kind"] not in kinds:
                raise BadInput(f"nguyên liệu lạ: {it['kind']}")
            fresh = it["fresh"]
            if not isinstance(fresh, (int, float)) or isinstance(fresh, bool) or fresh < 0 or fresh > 100:
                raise BadInput(f"freshness ngoài [0, 100]: {fresh}")
        return data["items"]
    return validate_items(data["items"], kinds)


def hold_to_items(hold: list):
    """Khoang (mảng id hoặc mảng cá thể) -> danh sách xuất kho."""
    if hold and isinstance(hold[0], dict):
        return list(hold)
    counts = {}
    for k in hold:
        counts[k] = counts.get(k, 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def write_inventory(path: str, items):
    if isinstance(items, list):
        out_items = items
    else:
        out_items = {k: items[k] for k in sorted(items) if items[k] > 0}
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": out_items}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
