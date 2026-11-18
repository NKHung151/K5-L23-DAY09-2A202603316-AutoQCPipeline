# Báo cáo Day 09 — Nguyễn Khải Hưng, 2A202603316

## 1. Kết luận trước
Pipeline kết luận **Hold** (mã thoát 10). Lô 224 ảnh: cửa vào loại 21, còn **203 ảnh** đi tiếp và được xuất thành **bản NHÁP** `submission/export/clean_v1/` (chưa phải bản phát hành).
Lý do: không còn lỗi bắt buộc, nhưng hàng đợi người duyệt có 118 ảnh trong khi ngân sách chỉ 80, nên **29/203 ảnh (14,3%)** còn cảnh báo chưa ai xem, vượt ngưỡng 10% (`08_summary.json`).

## 2. Lỗi và phân việc
Lấy từ `02_error_list_v1` (193 dòng; số ảnh có lỗi trên mẫu số 224 ảnh trước intake, hoặc 203 sau intake với lỗi nhãn).

| Mã lỗi | Số ảnh/dòng | Ai sửa | Vì sao |
|---|---:|---|---|
| CORRUPT_IMAGE / BAD_SIZE | 2 / 3 | máy (loại ảnh) | ảnh không dùng được, không có gì để sửa |
| DUP_IMAGE_EXACT / DUP_IMAGE_NEAR | 8 / 3 | máy (loại ảnh) | trùng ảnh, loại bản sau |
| LEAK_TEST | 5 | máy (loại ảnh) | rò rỉ từ tập test, phải loại để đo công bằng |
| BAD_CLASS_NAME | 1 ảnh (`data.yaml`) | máy | ghi lại `names` đúng cấu hình |
| BAD_FORMAT / BAD_CLASS_ID / BOX_ZERO / DUP_BOX | 3 / 6 / 4 / 7 dòng | máy (xoá dòng) | dòng hỏng, không có gì để giữ |
| BOX_OUT_OF_IMAGE | 8 dòng | máy (cắt về trong ảnh) | giữ lớp, chỉ cắt toạ độ |
| MISSING_LABEL_FILE | 6 ảnh | **người** | máy không được bịa nhãn (`needs_label`) |
| POSSIBLE_MISSING / WRONG_CLASS / LOOSE_BOX / FALSE_POS | 43 / 16 / 21 / 27 ảnh | **người** | chỉ là nghi ngờ của model lớn, cần mắt người |
| EMPTY_LABEL, BOX_TINY, BOX_HUGE, CLASS_RARE | 12 / 4 / 3 / 1 ảnh | **người** | cảnh báo quy tắc, ý nghĩa do người quyết |

Tổng số thay đổi tự động: 35 (`03_fixes.csv`: 20 `drop_line`, 8 `clip_box`, 6 `needs_label`, 1 `rename_classes`). Sau sửa còn 6 lỗi bắt buộc, đều là `MISSING_LABEL_FILE`.

Hàng đợi (`05_review_queue.csv`, 118 ảnh) xếp theo điểm ưu tiên = tổng trọng số của mã cảnh báo (trọng số cố định trong cấu hình): ảnh `NEEDS_LABEL` (thiếu hẳn file nhãn, trọng số 10) lên đầu vì chỉ người mới gán được, kế đến ảnh có nhiều nghi ngờ ngữ nghĩa (`POSSIBLE_WRONG_CLASS` 3, `POSSIBLE_MISSING` 2…). Người duyệt được 80/118 ảnh. Hiệu quả (v1 → v3): `POSSIBLE_MISSING` 44 → 6, `POSSIBLE_WRONG_CLASS` 16 → 2, `POSSIBLE_LOOSE_BOX` 22 → 11, `POSSIBLE_FALSE_POS` 29 → 21, `MISSING_LABEL_FILE` 6 → 0. 38 ảnh còn lại của hàng đợi không ai xem.

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | **8** | DUP_IMAGE_NEAR: 1,00 / 0,50 → 1,00 / 0,67 | Precision vẫn 1,00 (loại sai ảnh tốt là lỗi đắt). Từ 4 đến 14 recall không đổi, chọn 8 để có biên an toàn. |
| `second_opinion.conf` | 0.25 | **0.7** | MISSING: 0,50 / 1,00 → 0,58 / 0,88; WRONG_CLASS: 0,56 / 0,83 → 0,62 / 0,83 | Tăng conf bớt báo động giả (hàng đợi 145 → 118 ảnh) mà recall MISSING chỉ mất 1 ca. Không chọn 0.8: gate thành Release (7,9%) nhưng recall MISSING xuống 0,75, tức là Release nhờ checker bớt nhạy. |

**Chỗ calibration có thể đánh lừa:** calib cho `phash_dist = 16` là tốt nhất (recall 0,83, F1 0,91), nhưng chỉ có 6 ảnh gần trùng nên 0,67 so với 0,83 chênh đúng 1 ảnh. Trên raw, 16 loại **31** ảnh so với 22 ở mức 12 (thêm 9 ảnh chỉ khi tăng 4 đơn vị), dấu hiệu ảnh khác nhau bị coi là trùng. Vì vậy chọn 8. Ở 8 tôi mở xem cặp ảnh duy nhất có phash khác 0 (`img_0223` ~ `img_0077`, phash 6): cùng một cảnh khác kích thước và độ sáng, loại là đúng. Hai ảnh gần trùng còn lại có phash 0.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
**Lỗi tự quan sát bằng mắt** (`scripts/viz_labels.py img_0001 img_0030`, ảnh ở `work/viz/`):
1. `img_0001`: thiếu nhãn `person` cho người lính bên phải. Máy chỉ nghi ngờ (`POSSIBLE_MISSING`, conf 0,95); ảnh nằm trong hàng đợi và được người duyệt.
2. `img_0001`: dòng 1 và dòng 3 gần như trùng hẳn, cùng lớp (`DUP_BOX` dòng 3, máy xoá dòng 3 trong `03_fixes.csv`).
3. `img_0030`: dòng 9 có `cx = -0,0038`, tràn ảnh 0,023 (`BOX_OUT_OF_IMAGE`). Máy cắt về trong ảnh, nhưng box sau cắt chỉ rộng 0,015 nên bị `BOX_TINY` và `POSSIBLE_FALSE_POS`, ảnh vào hàng đợi.
4. `img_0070`: người phụ nữ bên trái bị gán `car` (đúng ra `person`), máy cờ `POSSIBLE_WRONG_CLASS`.
5. `img_0020`: xe buýt bị gán `truck` (đúng ra `bus`), và dòng 3 có id lớp `93` (`BAD_CLASS_ID`, máy xoá dòng đó).
6. `img_0160`: một xe tải bị gán `bus`, và bãi xe tải rất nhiều xe nhưng nhãn chỉ có 4 box (`POSSIBLE_MISSING`, thiếu nhãn hàng loạt).

Người chỉ lộ một phần ở mép ảnh mà vẫn gán `person` là đúng quy ước, không phải lỗi.

**(a) Chứng minh gate chặn đúng.** Chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb`: không có người duyệt nên 6 ảnh thiếu file nhãn còn nguyên. Kết quả: `REWORK — còn 6 lỗi bắt buộc chưa xử lý`, mã thoát **20**, log ghi "KHÔNG xuất", và thư mục `work/exp_nb` **không được tạo**.

**(b) Điểm mù có bằng chứng (từ `calibration_report.md`, conf 0.7 / phash 8):**
- **Ảnh gần trùng biến đổi mạnh:** `DUP_IMAGE_NEAR` recall chỉ 0,67 (4/6): 2 ảnh trùng gần chèn trong calib lọt qua. Ngoài ra không có cách bắt ảnh bị cắt mạnh rồi thu nhỏ bằng phash.
- **Box lỏng:** `POSSIBLE_LOOSE_BOX` recall 0,20 (1/5 ca chèn), precision 0,50. Box lệch nhẹ gần như không bị bắt.
- **Báo động giả của FALSE_POS:** precision chỉ 0,31 (11 FP so với 5 TP trên calib). Trên raw, `POSSIBLE_FALSE_POS` còn 21 ảnh sau người duyệt; tôi chưa mở xem từng ảnh nên chưa biết bao nhiêu là lỗi thật, nhưng precision thấp trên calib cho thấy nhiều khả năng phần lớn là báo động giả.
- **Model cũng nhầm:** nếu yolo26l và nhãn cùng nhầm lớp (xe tải/xe con), máy im lặng.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Cấu hình (giống nhau cho mọi lần chạy): `yolo26n.pt`, 20 epoch, imgsz 640, batch 16, seed 0 và 1, GPU T4 (Colab); val = `gold_val` (40 ảnh), test = `data/test` (100 ảnh). Chỉ khác dữ liệu train (`submission/results/comparison.md`, do `scripts/summarize_results.py` sinh):

| biến thể | #ảnh train | số seed | mAP50 | mAP50-95 | precision | recall |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0,726 ± 0,000 | 0,512 ± 0,004 | 0,764 ± 0,061 | 0,649 ± 0,028 |
| clean | 203 | 2 | 0,699 ± 0,013 | 0,489 ± 0,016 | 0,804 ± 0,092 | 0,588 ± 0,065 |

**Kết quả:** chênh mAP50 (clean − raw) = **−0,026**: `clean` **không tốt hơn** `raw` mà thấp hơn. Độ lệch giữa 2 seed: 0,0003 ở `raw` (0,7256 và 0,7259) và 0,018 ở `clean` (0,690 và 0,709). Hai khoảng giá trị không chồng nhau, nhưng mỗi biến thể chỉ có 2 seed và test chỉ có 100 ảnh nên không đủ để kết luận `clean` kém hơn nói chung. AP50 theo lớp (trung bình 2 seed, raw → clean): car 0,738 → 0,744; person 0,822 → 0,822; bus 0,695 → 0,690; **truck 0,648 → 0,541** (giảm 0,107, gần như toàn bộ phần chênh). Precision của `clean` cao hơn (0,804 so với 0,764) còn recall thấp hơn (0,588 so với 0,649).

**Kết luận trung thực:** trong thí nghiệm này pipeline không cải thiện mAP50 trên tập test; không có bằng chứng để nói dữ liệu sau pipeline tốt hơn. Phần lớn chênh lệch nằm ở lớp `truck`, lớp ít box nhất (32 box trong `raw`, 40 trong `clean`), nên rất nhiễu.

**Giả thuyết giải thích (chưa kiểm chứng, kèm cách kiểm):**
1. **Rò rỉ làm `raw` bị thổi phồng:** `raw` chứa 5 ảnh `LEAK_TEST` trùng với ảnh test (`01_intake.csv`), tức model đã thấy ảnh test lúc train. Cách kiểm: train thêm biến thể `raw` đã bỏ 5 ảnh này, hoặc tính mAP trên test đã bỏ 5 ảnh bị trùng, rồi so lại.
2. **`clean` còn nhãn máy chưa được người duyệt:** hàng đợi 118 ảnh nhưng chỉ duyệt 80, còn 29/203 ảnh (14,3%) cảnh báo (`07_error_list_v3`), và `clean` ít ảnh hơn `raw` 21 ảnh (203 so với 224). Cách kiểm: train biến thể `oracle` (cùng ảnh `clean`, nhãn người) làm chặn trên; nếu `oracle` vượt `raw` thì nhãn còn lỗi mới là nguyên nhân.
3. **Test nhỏ và lớp `truck` hiếm:** 100 ảnh test, `truck` chỉ có vài chục box nên AP biến động mạnh theo seed. Cách kiểm: chạy ≥ 5 seed mỗi biến thể rồi so chênh với độ lệch chuẩn.

Hạn chế: `train_images` là số file trong thư mục train; số ảnh Ultralytics thực sự dùng của `raw` có thể ít hơn vì nó bỏ ảnh/nhãn hỏng. Tôi chưa đối chiếu cảnh báo trong log Colab nên chưa khẳng định con số đó.

**Việc tiếp theo:** train `oracle` và `raw` bỏ ảnh rò rỉ, tăng số seed lên ≥ 5, và duyệt nốt hàng đợi để `clean` đạt Release rồi so lại.

## 6. Quyết định và ghi chú AI
(a) **Quyết định: Hold.** Không có lỗi bắt buộc nhưng 29/203 ảnh (14,3%) còn cảnh báo chưa người duyệt. Để thành Release cần ≤ 20 ảnh còn cảnh báo (10% của 203), tức là người cần duyệt thêm ít nhất 9 ảnh trong 29 ảnh đó (chủ yếu `POSSIBLE_FALSE_POS` và `POSSIBLE_LOOSE_BOX`), hoặc một đợt duyệt khác ngoài ngân sách 80 ảnh. Ngưỡng và ngân sách không được đổi.

(b) Ghi chú AI: có dùng Claude Code để viết 4 module và chạy calibrate.
- **Prompt chính:** đọc toàn bộ dự án rồi viết `label_format`, `gate`, `autofix`, `second_opinion` theo docstring, tránh ngưỡng viết cứng.
- **Cách kiểm:** chạy `pytest` (79 test của đề xanh, nay 89 với 10 test thưởng), chạy `pipeline.run`, đối chiếu `img_0001`/`img_0030` với nhãn gốc bằng `viz_labels.py`, mở xem cặp ảnh bị coi là trùng, so ngưỡng trên calib với raw.
- **Một lần AI sai:** AI nhận định box tràn ảnh ở `img_0030` "cắt xong vẫn còn diện tích nên ổn", nhưng thực tế sau khi cắt box chỉ rộng 0,015 và bị cờ `BOX_TINY`/`POSSIBLE_FALSE_POS`; chỉ phát hiện khi đọc `03_fixes.csv` và `02_error_list_v1`.

**Thưởng +3: check mới `aspect_ratio`** (`pipeline/checks/aspect_ratio.py`, test `tests/test_aspect_ratio.py`, 10 test xanh). Cảnh báo `BOX_ASPECT_ODD` (WARN) khi tỉ lệ rộng/cao của box **tính bằng pixel** vượt 8 (ngưỡng đọc từ `cfg["aspect_ratio"]["max_ratio"]`, mặc định 8). Là module độc lập, không đăng ký trong `checks/__init__.py` (file đề bị ghim) nên `make run` không chạy nó và kết luận Hold không đổi. Chạy tay trên `work/run/ds` (203 ảnh sau sửa): 3 cảnh báo ở 3 ảnh: `img_0030` dòng 9 (tỉ lệ 8,6), `img_0042` dòng 5 (9,6), `img_0155` dòng 2 (9,8). Dòng 9 của `img_0030` chính là box tràn mép trái do `autofix` cắt xuống còn rộng 0,015 (xem mục 4), nên check này bắt được tác dụng phụ của việc cắt box.
