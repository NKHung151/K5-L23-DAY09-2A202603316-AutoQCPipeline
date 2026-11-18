# Phân tích kết quả train: raw vs clean

Nguồn số liệu: `raw_seed{0,1}.json`, `clean_seed{0,1}.json`, `comparison.md` (do script sinh), `../reports/*`, `../REPORT.md` mục 5.
Cấu hình chung: `yolo26n.pt`, 20 epoch, imgsz 640, batch 16, seed 0 và 1, val = `gold_val` (40 ảnh), test = `data/test` (100 ảnh).

| biến thể | #ảnh train | mAP50 (seed 0 / seed 1) | mAP50 TB ± độ lệch | mAP50-95 TB | precision TB | recall TB |
|---|---|---|---|---|---|---|
| raw | 224 | 0,7256 / 0,7259 | 0,726 ± 0,000 | 0,512 | 0,764 | 0,649 |
| clean | 203 | 0,6902 / 0,7085 | 0,699 ± 0,013 | 0,489 | 0,804 | 0,588 |

## 1. Chênh mAP50 so với độ lệch giữa các seed
- Chênh mAP50 (clean − raw) = **−0,026**: `clean` thấp hơn `raw`.
- Độ lệch giữa 2 seed: `raw` ≈ 0,0003 (hai seed gần như y hệt), `clean` ≈ 0,018. Chênh −0,026 lớn hơn độ lệch của `clean` (0,018) và lớn hơn nhiều so với của `raw`; hai khoảng giá trị (raw 0,7256–0,7259, clean 0,690–0,709) không chồng nhau.
- Kết luận được đến đâu: chỉ có 2 seed mỗi biến thể và test 100 ảnh, nên độ lệch chuẩn từ 2 điểm rất không đáng tin (`raw` ra 0,000 là trùng hợp, không phải bằng chứng ổn định). Có thể nói: **không có bằng chứng `clean` tốt hơn `raw`**; chưa đủ để nói `clean` kém hơn nói chung.

## 2. `raw` thật sự train trên bao nhiêu ảnh?
- `train_images = 224` là **số file** trong thư mục train, không phải số ảnh Ultralytics thực sự dùng.
- Ultralytics bỏ qua ảnh hỏng và ảnh có nhãn không hợp lệ (đây là suy luận từ hành vi của thư viện, **chưa đối chiếu với log Colab**). Theo `02_error_list_v1`, `raw` có 19 ảnh thuộc nhóm có thể bị bỏ: 2 ảnh hỏng (`CORRUPT_IMAGE`), ảnh có dòng sai định dạng (`BAD_FORMAT`), ID lớp ngoài 0..3 (`BAD_CLASS_ID`, gồm id −1, 4, 7, 93) hoặc box tràn ảnh (`BOX_OUT_OF_IMAGE`). Nếu tất cả bị bỏ thì `raw` chỉ train trên khoảng **205/224 ảnh**, gần bằng 203 ảnh của `clean`.
- Cách kiểm: đọc các dòng `WARNING` / "ignoring corrupt image/label" ở ô 6 của notebook cho phần train `raw`.

## 3. `raw` có ảnh trùng với tập test không?
- **Có.** `01_intake.csv` ghi 5 ảnh `LEAK_TEST` trong `raw`: `img_0049` (test_033), `img_0101` (test_039), `img_0167` (test_044), `img_0174` (test_085), `img_0221` (test_009). Đã xem bằng mắt: cùng một cảnh.
- Hệ quả: model train trên `raw` đã thấy 5/100 ảnh test, nên điểm của `raw` có thể bị thổi phồng. **Chưa đo được mức thổi phồng** vì chưa train lại.
- Cách kiểm: (a) train biến thể `raw` đã bỏ 5 ảnh này rồi so lại với `raw` đầy đủ; hoặc (b) tính mAP trên test đã bỏ 5 ảnh bị trùng. Cả hai cần chạy thêm.
- Ghi chú: 5 ảnh rò rỉ không thuộc nhóm 19 ảnh ở mục 2, nên chúng vẫn được `raw` dùng để train.

## 4. Lớp nào được lợi nhất?
AP50 theo lớp (TB 2 seed):

| lớp | raw | clean | clean − raw |
|---|---|---|---|
| car | 0,738 | 0,744 | +0,007 |
| person | 0,822 | 0,822 | 0,000 |
| truck | 0,648 | 0,541 | **−0,107** |
| bus | 0,695 | 0,690 | −0,005 |

- **Không lớp nào được lợi rõ rệt**: car +0,007 và person 0,000 nằm trong nhiễu. Gần như toàn bộ chênh lệch mAP50 nằm ở `truck`.
- `truck` là lớp ít box nhất: 32 box trong nhãn `raw` gốc, 40 box trong `clean` (`clean` nhiều hơn vì người duyệt mô phỏng đã sửa/gán thêm), nên AP của lớp này biến động rất mạnh theo seed (clean seed 0: 0,503; seed 1: 0,578).
- Liên hệ lỗi nhãn: `data/README.md` nói lỗi ngữ nghĩa của `raw` nghiêng về nhầm car/truck/bus, và `02_error_list_v1` có 16 ảnh `POSSIBLE_WRONG_CLASS`. Chưa có dữ liệu tách theo lớp để khẳng định các lỗi này nằm ở `truck`, nên đây mới là giả thuyết.

## 5. `clean` còn lỗi gì? Có phải chặn trên của dữ liệu sạch không?
- Hàng đợi người duyệt có **118 ảnh**, vượt ngân sách **80** ảnh: 38 ảnh không ai xem.
- Sau người duyệt, `07_error_list_v3` còn 53 cảnh báo trên **29/203 ảnh (14,3%)**: `POSSIBLE_FALSE_POS` 21, `POSSIBLE_LOOSE_BOX` 11, `POSSIBLE_MISSING` 6, `POSSIBLE_WRONG_CLASS` 2, `BOX_TINY` 7, `EMPTY_LABEL` 4, `BOX_HUGE` 2. Kết luận của pipeline là **Hold**; `clean_v1` là bản nháp.
- Vì vậy `clean` **chưa phải chặn trên** của dữ liệu sạch: nó vẫn còn nhãn máy chưa qua mắt người. Để biết chặn trên thật cần train biến thể `oracle` (cùng ảnh, nhãn người).

## Kết luận và việc tiếp theo
- Trong thí nghiệm này pipeline **không cải thiện** mAP50 trên test; không dùng kết quả này để nói dữ liệu sau pipeline tốt hơn.
- Nên làm tiếp (chưa làm): train `oracle`; tăng lên ≥ 5 seed; train `raw` bỏ 5 ảnh rò rỉ; đọc log Ultralytics để biết số ảnh `raw` thực sự dùng; duyệt nốt hàng đợi cho `clean`.
