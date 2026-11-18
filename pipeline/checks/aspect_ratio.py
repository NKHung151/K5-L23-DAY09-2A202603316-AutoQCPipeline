"""CHECK THƯỞNG — box có tỉ lệ khung hình bất thường (quá dài hoặc quá dẹt).

Test:  pytest tests/test_aspect_ratio.py -q

Vì sao cần: box bị kéo giãn một chiều thường là lỗi gán (kéo nhầm cạnh, box "phình to" hay bị cắt còn một lát mỏng),
mà các check hình học khác không thấy vì box vẫn nằm trong ảnh, không rỗng, không quá nhỏ.

Quy tắc: với mỗi dòng nhãn hợp lệ, tính tỉ lệ theo PIXEL (không theo toạ độ chuẩn hoá, vì ảnh không vuông):
    ratio = max(w*W, h*H) / min(w*W, h*H)
Nếu ratio > ngưỡng thì cảnh báo `BOX_ASPECT_ODD` (WARN: việc của người xem, máy không tự sửa).

Ngưỡng: `cfg["aspect_ratio"]["max_ratio"]` nếu có, ngược lại dùng MAX_RATIO mặc định bên dưới.
(Không thêm khoá mới vào configs/pipeline.yaml vì file đó bị cố định theo RULES.md.)

Module độc lập: chưa đăng ký trong `checks/__init__.py` (file đề bị ghim) nên `make run` không chạy nó;
gọi trực tiếp `aspect_ratio.run(ds, cfg)`.
"""
from ..common import WARN, Issue, parse_yolo_line

MAX_RATIO = 8.0     # person đứng ~2-3, xe buýt/xe tải nằm ngang ~2-4: vượt 8 gần như chắc chắn bất thường


def run(ds, cfg):
    limit = float(cfg.get("aspect_ratio", {}).get("max_ratio", MAX_RATIO))
    issues = []
    for p in ds.label_files():
        stem = p.stem
        size = ds.image_size(stem)
        if not size:                                  # không có ảnh / ảnh hỏng: không tính được pixel
            continue
        W, H = size
        for n, text in ds.read_label_lines(stem) or []:
            try:
                cls, _, _, w, h = parse_yolo_line(text)
            except ValueError:
                continue                              # dòng hỏng: check label_format báo
            if not 0 <= cls < len(ds.classes) or w <= 0 or h <= 0:
                continue                              # id lạ / box rỗng: cũng của label_format
            wp, hp = w * W, h * H
            ratio = max(wp, hp) / min(wp, hp)
            if ratio > limit:
                kind = "quá dẹt (rộng hơn cao)" if wp > hp else "quá dài (cao hơn rộng)"
                issues.append(Issue("aspect_ratio", WARN, "BOX_ASPECT_ODD", stem,
                                    f"box {kind}: tỉ lệ {ratio:.1f} > {limit:g}", n, {"ratio": round(ratio, 2)}))
    return issues
