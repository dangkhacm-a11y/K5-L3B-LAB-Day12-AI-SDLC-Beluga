# Sửa luồng Live Gather → Quán

## Nguyên nhân và thay đổi

Live dừng sau Gather, chỉ lưu kho nếu truyền `--inventory-out`. Handler Quán
trỏ đến `restaurant.html` không tồn tại dù `web/index.html` đã vẽ được cả hai màn.

Sửa file khung `chonoi/live.py` để lưu kho mặc định vào `inventory.json` (hoặc
đích `--inventory-out`), rồi tạo Session Quán với `inventory_items()` của Gather.
Trạng thái/metadata đổi sang Quán để client hiện màn Quán và HUD kho sẵn có.
Ghi file lỗi thì giữ Gather/giỏ, báo lỗi và thử lại trước khi chuyển màn.
Restart trả về mode/seed/scenario ban đầu. Handler phục vụ trang dùng chung.
Không sửa luật mô phỏng, contract, schema kho hoặc luồng headless.

## Kiểm chứng

Đã chạy test mới trước khi sửa: thiếu file kho mặc định, không chuyển mode,
không báo lỗi lưu và HTTP 404 ở trang Quán được tái hiện.

Sau khi sửa, chạy:

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
git diff --check
```

Kết quả: **118 tests, OK, 3.696 giây**; diff không có lỗi whitespace.
Log đầy đủ: [live-gather-quan-tests.txt](live-gather-quan-tests.txt).

Test bổ sung kiểm cập bến/hết giờ/ngất, kho lưu đúng/sang Quán đúng, không ghi
trước khi kết thúc hoặc ghi lại khi đang ở Quán, restart, lưu lỗi rồi khôi phục,
và HTTP `/input` → `/state` → tải trang Quán.

Chrome headless với profile tạm đã mở server thật ở 1280×800 và 390×844.
Đối chiếu kho file và state: `{"ca_loc":1,"bong_sung":2}`. Kiểm ảnh xác nhận
màn Quán hiển thị dòng “Kho: bông súng×2, cá lóc×1” ở cả hai kích thước.
Ảnh desktop: [live-gather-quan.png](live-gather-quan.png).
Khung game hiện hữu vẫn bị cắt bên phải ở viewport hẹp; bản sửa không đổi layout.

Review độc lập bản diff: không phát hiện lỗi cần xử lý.
