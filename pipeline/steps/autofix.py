"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict  # noqa: F401

import yaml  # noqa: F401

from ..common import ERROR, parse_yolo_line  # noqa: F401


DROP_LINE = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_IMAGE = {"DUP_IMAGE_EXACT", "DUP_IMAGE_NEAR", "LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def _fmt(v):
    return f"{v:.6f}".rstrip("0").rstrip(".") or "0"


def fix(ds, issues, cfg):
    fixes = []
    errs = [i for i in issues if i.severity == ERROR]

    def log(image, line, action, before, after):
        fixes.append({"image": image, "line": line, "action": action, "before": before, "after": after})

    # 1) xoá ảnh (và nhãn)
    removed = set()
    for i in errs:
        if i.code in REMOVE_IMAGE and i.image not in removed:
            removed.add(i.image)
            p = ds.image_path(i.image)
            before = p.name if p else "(không có file)"
            if p:
                p.unlink()
            if ds.label_path(i.image).exists():
                ds.label_path(i.image).unlink()
            log(i.image, "", "remove_image", before, "(đã xoá)")

    # 2) data.yaml
    if any(i.code == "BAD_CLASS_NAME" for i in errs):
        before = [ds.yaml_names().get(k) for k in range(len(cfg["classes"]))]
        d = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
        d["names"] = list(cfg["classes"])
        ds.yaml_path.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
        log("data.yaml", "", "rename_classes", str(before), str(list(cfg["classes"])))

    # 3) thiếu file nhãn: chuyển người, không bịa file
    for i in errs:
        if i.code == "MISSING_LABEL_FILE" and i.image not in removed:
            log(i.image, "", "needs_label", "(không có file)", "chuyển người gán")

    # 4) lỗi cấp dòng: gom theo ảnh, ghi MỘT lần (số dòng trong issue là số dòng GỐC)
    by_img = defaultdict(lambda: {"drop": set(), "clip": set()})
    for i in errs:
        if i.image in removed or i.line is None:
            continue
        if i.code in DROP_LINE:
            by_img[i.image]["drop"].add(i.line)
        elif i.code == "BOX_OUT_OF_IMAGE":
            by_img[i.image]["clip"].add(i.line)

    for stem, g in by_img.items():
        path = ds.label_path(stem)
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
        out = []
        for n, text in enumerate(raw, 1):
            if not text.strip():
                continue                      # dòng trống: bỏ, nhưng đã được đếm vào n
            if n in g["drop"]:
                log(stem, n, "drop_line", text, "(đã xoá)")
                continue
            if n in g["clip"]:
                try:
                    cls, cx, cy, w, h = parse_yolo_line(text)
                except ValueError:
                    out.append(text)
                    continue
                x1, x2 = max(0.0, cx - w / 2), min(1.0, cx + w / 2)
                y1, y2 = max(0.0, cy - h / 2), min(1.0, cy + h / 2)
                if x2 - x1 <= 0 or y2 - y1 <= 0:
                    log(stem, n, "drop_line", text, "(đã xoá: nằm ngoài ảnh)")
                    continue
                new = f"{cls} {_fmt((x1 + x2) / 2)} {_fmt((y1 + y2) / 2)} {_fmt(x2 - x1)} {_fmt(y2 - y1)}"
                log(stem, n, "clip_box", text, new)
                out.append(new)
                continue
            out.append(text)
        path.write_text("".join(t + "\n" for t in out), encoding="utf-8")
    return fixes
