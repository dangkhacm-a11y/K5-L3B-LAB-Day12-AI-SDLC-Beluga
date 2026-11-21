# Sửa giỏ và kết thúc Gather — 2026-11-21

## Nguyên nhân và phạm vi

- Gather tạo `{id, kind, fresh}` ngay cả với contract v1.1, trong khi UI, ghi kho và luồng cũ còn nhận chuỗi/số lượng.
- Tái hiện trước sửa: giỏ hiện `[object Object]×3`; ghi kho ném `TypeError` khi sắp xếp/index bằng object. Live Quán cũng dùng `dict(stock)` và `reserved.items()` trên mảng cá thể/ID.
- Gather giữ biểu diễn v1.1 khi chưa bật `freshness` và chưa nạp cá thể; Phase 3 tiếp tục giữ ID, độ tươi và LIFO. Không sửa test cũ để đổi kỳ vọng.
- Sửa starter `inventory.py` vì điểm ghi dùng chung phải gom cá thể thành số lượng; schema file vẫn `{"items":{"ca_loc":1}}`. Sửa `live.py` để dùng `QuanSim.available_stock()` có sẵn. Không sửa runner, CLI headless, contract hay `docs/contracts/`.
- Live chuyển trực tiếp các cá thể sang Quán để giữ ID/độ tươi. File kho hiện tại chỉ lưu số lượng theo contract v1.1; không lưu độ tươi để nạp lại giữa hai tiến trình.
- Canvas dùng `kind` để tô màu/đếm giỏ, hỗ trợ cả kho đếm và kho cá thể khi vẽ Quán. Giữ giao diện hiện có.

## Kiểm chứng

Đã chạy test mới trước sửa, thấy lỗi ghi kho đúng tại `write_inventory`. Chrome trước sửa có 4 kiểm tra thất bại với dữ liệu cá thể, ở hai kích thước 1280 và 390.

```text
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
Ran 139 tests in 3.689s
OK

python3 tools/check_gather_ui.py
14/14 PASS (Chrome headless, Canvas thật; chiều rộng 1280 và 390)

git diff --check
exit 0
```

Bao gồm cập bến/hết giờ/ngất, lưu thất bại rồi thử lại, restart, HTTP, chuyển kho sang nấu, và Phase 3 giữ nguyên ID/độ tươi khi chuyển màn. Khách giữ cá thể theo ID vẫn trả `/state` với kho khả dụng đúng.

Audit UI tĩnh strict bằng `frontend-design-premium/scripts/audit_project.py`: 0 findings. Kiểm Chrome gọi hàm vẽ thật với fixture giỏ/kho rỗng, v1.1 và cá thể; kiểm tên, số lượng và màu. Đây là kiểm renderer, không phải tự động chơi toàn bộ luồng bằng bàn phím trong Chrome; HTTP và chuyển màn được kiểm bằng unittest.

## Ghép conflict sau cập nhật upstream `443e382`

Quyết định sau đây thay thế giới hạn file kho ở bản sửa ban đầu bên trên:

- `inventory.py`: giữ upstream, gồm đọc/ghi cả kho đếm v1.1 và mảng cá thể v1.2. Ghi mảng giữ nguyên ID/độ tươi, không chạy `sorted()` trên object. `hold_to_items()` giữ cá thể khi nhận mảng cá thể và đếm khi nhận chuỗi.
- `live.py`: giữ `sim.available_stock()` từ stash; upstream trừ `I9` như tên nguyên liệu khi `reserved` chứa ID, dẫn tới kho khả dụng sai. Giữ các thay đổi phím/metadata upstream ngoài conflict.
- `index.html`: giữ bảng màu, tên món, hoạt ảnh, thanh độ tươi và HUD upstream; ghép helper đếm loại cùng dòng tên/số lượng giỏ từ stash. Không chọn toàn bộ file từ một phía.
- Đổi test mới `test_inventory_records` và kỳ vọng file trong test Live cá thể vì upstream `9f121d5` đã thêm file kho v1.2: cần kiểm roundtrip giữ ID/độ tươi. Các test v1.1 cũ giữ nguyên kỳ vọng kho đếm. Công cụ Chrome theo bảng màu/nội dung mới và truyền thời gian hoạt ảnh cố định.
- Review phát hiện dòng tổng hợp giỏ có thể chồng hướng dẫn phím ở 900px; tăng vùng HUD dưới 15px để dành hai dòng riêng. Kiểm Chrome dùng `measureText()` xác nhận hai dòng không chạm nhau.
- Kiểm lại sau ghép: toàn bộ 139 unittest qua; 21/21 kiểm renderer Chrome qua (giỏ/kho rỗng, chuỗi/đếm, cá thể, chiều rộng 1280, 900 và 390).
