# Thành viên 3 — triển khai Quán theo PRD-0

Nguồn yêu cầu: `Task.md` và PRD đầy đủ do người dùng cung cấp ngày 2026-11-21.
Tài liệu này thay thế giả định trước khi có PRD, tập trung Test Contract D–F.

1. Khách theo phase_tick, bàn trống ID nhỏ nhất, món đủ tồn khả dụng từ danh
   sách sắp Unicode và RNG `customer_order`. Giữ công thức khi đặt; chỉ tiêu
   tồn khi bắt đầu nấu. Full bàn bỏ lượt; thiếu món phát `no_dish` với `{}`.
2. Customer `state=waiting/eating` tách biệt `order_status`. Dùng đủ các
   trạng thái `reserved/assigned/unfulfillable/served`; món có
   `{order_id,dish_id,base_price}`. Fixture sai phải mã 2 trước khi ghi output.
3. Tích hợp lát 4: giảm timer → bếp chín → move/interact → quyết toán theo
   ID bàn → closing hoặc khách mới. Phục vụ ở patience 0/hết ca hợp lệ.
   Closing trả khách đang ăn ngay; khách chờ rời không giảm uy tín. Bỏ món
   của đơn rời, nhả giữ thô, không hoàn nguyên liệu đã dùng.
4. UI live tiếng Việt: sàn bè, bếp/bàn/Út Sen, đơn, kiên nhẫn, kho khả dụng,
   món cầm, tiền/uy tín; bàn phím và nút cảm ứng. Live dùng cùng Session;
   kho thử chỉ bật qua `scenarios/restaurant-demo.json`.
5. Kiểm chứng lifecycle, schema/event exact, deadline, tip, closing, RNG,
   deterministic replay, E2E kho và browser desktop/mobile/offline/restart.

## Tích hợp trên nền mã mới

Trong phiên, checkout cập nhật tới `d67330a` (đã ghép lát 1, 2 và 4). Giữ
logic di chuyển/chọn mục tiêu tương tác; sửa phần tích hợp bếp/thu tiền để
khớp PRD mới cung cấp. `tests/test_quan_member4.py` và
`tests/test_integration_gather_quan.py` trước đó dùng món dạng chuỗi,
`customer_id`, `dish`, `price/total` và `patience_ticks`. Chuyển fixture/assert
sang payload/schema PRD (`order_id`, `dish_id`, `base_price/amount`,
`patience_ticks_left`) và thêm liên kết assigned cho món; giữ nguyên ý nghĩa
các kiểm chứng, không bỏ assertion để làm xanh. Thành viên 4 review giao diện
này trước khi ghép.

`scenario.py` bổ sung validation D; `ids.py` chỉ nhận hậu tố số ASCII theo D;
`live.py` chỉ chọn màn Quán và metadata/HUD phụ. Không sửa contract, schema
kho, runner hoặc luật gather của các thành viên khác.

## Lệnh

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 -m chonoi.live --mode quan --scenario scenarios/restaurant-demo.json
python3 tools/check_restaurant_ui.py
```
