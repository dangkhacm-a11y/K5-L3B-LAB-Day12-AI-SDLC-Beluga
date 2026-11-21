# Thành viên 3 — Quán Phase 2 (TICKET-02)

## Lát Phase 2 đang thực hiện

Nguồn: `Task.md` và TICKET-02 người dùng cung cấp. Kế thừa vòng đời khách,
giữ nguyên liệu, thứ tự tick và payload D–F bên dưới; không viết lại engine.

1. Cập nhật riêng tuning `quan`/`menu`: B1/B2, T1–T4, đủ sáu món theo
   ticket; mở danh sách nguyên liệu kho cho `ca_keo`/`keo_neo`, giữ schema.
2. Bổ sung `QuanSim(..., inventory=None, *, allowed_dishes=None)`.
   Thành viên 4 truyền `allowed_dishes=day_plan["dishes"]` khi dựng Quán
   (map được duyệt theo khóa). Không truyền thì dùng toàn bộ menu.
   Lọc ID món trước khi lọc kho khả dụng; không dùng số suất làm hạn mức bán.
   Fixture khách ngoài kế hoạch hoặc giữ quá kho bàn giao bị `BadInput`.
3. Kiểm tuning công thức, giá, thời gian, tọa độ/ID bếp và bàn. Không đổi
   schema khách/món/event. Member 4 giữ điều phối tiền/earned/uy tín qua ngày,
   preset D1–D5, CLI day/pause và việc nâng version toàn manifest khi tích hợp.
4. Chuẩn bị regression Phase 2, sửa fixture P1 giả định chỉ có một bàn để
   giữ đúng ý nghĩa kiểm "đầy bàn". Người dùng tự chạy test; không ghi đạt,
   không commit/push/tag trước khi có kết quả.

Các thay đổi file khung `inventory.py`, `contract.py` chỉ phục vụ hai loại
nguyên liệu mới và kiểm dữ liệu Quán. Thông báo trong phiên và ghi lại đây
theo AGENTS.md; không đổi luật gather hay khối tuning gather.

## Bàn giao Phase 1 (lịch sử)

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
