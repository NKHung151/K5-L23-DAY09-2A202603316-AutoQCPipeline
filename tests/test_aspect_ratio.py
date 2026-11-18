from pipeline.checks import aspect_ratio


def run(make_ds, cfg, lines, size=(640, 480)):
    ds = make_ds(images={"a": 1}, labels={"a": lines}, size=size)
    return [(i.code, i.line) for i in aspect_ratio.run(ds, cfg)]


def test_normal_boxes_are_silent(make_ds, cfg):
    # person đứng (cao/rộng ≈ 3), xe nằm ngang (rộng/cao ≈ 2)
    assert run(make_ds, cfg, ["1 0.5 0.5 0.1 0.45", "0 0.3 0.3 0.3 0.2"]) == []


def test_very_wide_box_is_flagged_with_line_number(make_ds, cfg):
    # 0.9*640 = 576 px rộng, 0.05*480 = 24 px cao -> tỉ lệ 24
    assert run(make_ds, cfg, ["0 0.3 0.3 0.1 0.1", "2 0.5 0.5 0.9 0.05"]) == [("BOX_ASPECT_ODD", 2)]


def test_very_tall_box_is_flagged(make_ds, cfg):
    # 0.02*640 = 12.8 px rộng, 0.9*480 = 432 px cao -> tỉ lệ ~33
    assert run(make_ds, cfg, ["1 0.5 0.5 0.02 0.9"]) == [("BOX_ASPECT_ODD", 1)]


def test_ratio_is_measured_in_pixels_not_normalized_units(make_ds, cfg):
    # chuẩn hoá w=0.3, h=0.9 (tỉ lệ 3), nhưng ảnh 1000x100 -> 300 x 90 px, tỉ lệ 3,3: vẫn bình thường
    assert run(make_ds, cfg, ["0 0.5 0.5 0.3 0.9"], size=(1000, 100)) == []
    # chuẩn hoá w=h=0.5 (vuông), nhưng ảnh 1000x100 -> 500 x 50 px, tỉ lệ 10: bất thường
    assert run(make_ds, cfg, ["0 0.5 0.5 0.5 0.5"], size=(1000, 100)) == [("BOX_ASPECT_ODD", 1)]


def test_exact_limit_is_not_flagged(make_ds, cfg):
    # 640*0.4 = 256 px, 480*0.0666667 = 32 px -> tỉ lệ đúng 8 (không báo, chỉ báo khi > ngưỡng)
    assert run(make_ds, cfg, ["0 0.5 0.5 0.4 0.0666667"]) == []


def test_limit_comes_from_config(make_ds, cfg):
    lines = ["0 0.5 0.5 0.3 0.2"]                    # 192 x 96 px = tỉ lệ 2
    assert run(make_ds, cfg, lines) == []
    cfg["aspect_ratio"] = {"max_ratio": 1.5}
    assert run(make_ds, cfg, lines) == [("BOX_ASPECT_ODD", 1)]


def test_is_a_warning_with_ratio_in_extra(make_ds, cfg):
    ds = make_ds(images={"a": 1}, labels={"a": ["2 0.5 0.5 0.9 0.05"]})
    (i,) = aspect_ratio.run(ds, cfg)
    assert i.severity == "warn" and i.image == "a" and i.extra["ratio"] > 8


def test_blank_lines_keep_original_numbers(make_ds, cfg):
    assert run(make_ds, cfg, ["0 0.3 0.3 0.1 0.1", "", "", "2 0.5 0.5 0.9 0.05"]) == [("BOX_ASPECT_ODD", 4)]


def test_bad_lines_do_not_crash(make_ds, cfg):
    got = run(make_ds, cfg, ["garbage", "93 0.5 0.5 0.9 0.05", "1 0.5 0.5 0 0.3", "1 nan 0.5 0.2 0.3", "2 0.5 0.5 0.9 0.05"])
    assert got == [("BOX_ASPECT_ODD", 5)]               # chỉ dòng hợp lệ mới được xét


def test_label_without_image_is_skipped(make_ds, cfg):
    ds = make_ds(images={}, labels={"orphan": ["2 0.5 0.5 0.9 0.05"]})   # có nhãn mà không có ảnh: không tính được pixel
    assert aspect_ratio.run(ds, cfg) == []
