# Bàn giao thành viên 3 — Quán Phase 2

Nguồn: `Task.md`, TICKET-02 mục 1.3, 2, 4.3 và 4.5 do người dùng cung cấp.
Trạng thái: đã viết thay đổi và test; **chưa chạy test theo yêu cầu người dùng**.
Tài liệu này là hướng dẫn bàn giao, không phải kết quả smoke hoặc chứng nhận đạt.

Kiểm tĩnh trong phiên: `ast.parse` đọc cả năm file Python đã thay đổi/tạo mới
và `json.loads` đọc manifest, exit 0; `git diff --check`, exit 0. Không import
engine, không chạy test hay simulation. Các kiểm này chỉ xác nhận cú pháp/diff.

## Thay đổi

- `game.contract.json`: chỉ sửa `tuning.quan.stoves/tables` và `tuning.menu`.
  Hai bếp, bốn bàn, sáu công thức/giá/thời gian theo ticket; giữ `burn_s:null`.
- `chonoi/sim/quan.py`: thêm `allowed_dishes` dạng keyword, lọc ID món trước
  khi chọn đều bằng stream `customer_order` trên menu đủ kho chưa giữ.
  Món fixture ngoài kế hoạch bị `BadInput`; không giới hạn số lượt bán theo
  số suất. Thứ tự timer/chín → move/interact → quyết toán → closing/khách
  mới, giữ chỗ, thanh toán và event D–F được kế thừa từ Phase 1.
- `chonoi/inventory.py`: cho phép `ca_keo`, `keo_neo` qua tất cả đường nạp
  file kho, scenario.stock, reserved và kho trong bộ nhớ. Schema không đổi.
- `chonoi/contract.py`: kiểm menu/công thức, giới hạn uy tín, carry_limit,
  vị trí xuất phát và ID/tọa độ bếp/bàn; không sửa luật/validation gather.

Thông báo sửa contract/file khung trong phiên; ghi lý do tại
`docs/plan/member-3-restaurant.md` theo AGENTS.md.

## Thành viên 4 ghép day

```python
quan = QuanSim(tuning, quan_template, streams, ids,
               inventory=gather.inventory_items(),
               allowed_dishes=day_plan["dishes"])
quan.money = money
quan.earned = earned
quan.reputation = reputation
```

Truyền khối scenario `quan` (không phải scenario gốc). Không khai `stock`
khi có `inventory`. Lát 4 từ chối `quan.stock`/`quan.reputation` trong day;
kiểm món/kho sau khi gather kết thúc, khi đã có kho bàn giao thực.
`QuanSim` đã kiểm reservation và liên kết assigned theo kho đó.

Đọc lại `quan.money`, `quan.earned`, `quan.reputation` sau ca; `shift_earned`
bắt đầu từ 0. Không dùng số suất trong plan làm quota bán. Không truyền
`allowed_dishes` cho mode quan độc lập. Tiền/uy tín và pause do bộ điều phối
giữ; khi pause không gọi `QuanSim.step`, để lịch khách và timer đứng yên.
Thu thống kê DayResult/Summary từ event `served`, `paid`, `customer_left`.

Preset D1–D5, CLI day, Shop và nâng `contract_version` toàn manifest thuộc
lát 1/4. Bản hiện tại vẫn ghi version 1.0 vì gather/day chưa được tích hợp;
không coi bàn giao Quán là hoàn tất toàn bộ Test Contract v1.1.

## Người dùng chạy kiểm chứng

```bash
PYTHONPATH=tests:. python3 -m unittest tests.test_quan_phase2 tests.test_quan_customers tests.test_quan_contract tests.test_quan_member4 tests.test_integration_gather_quan -v
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```

| Yêu cầu ticket | Test chuẩn bị | Kết quả |
|---|---|---|
| 1.3: hai bếp/bốn bàn/sáu món | `test_ticket_menu_and_layout`, `test_standalone_can_order_every_dish` | Chưa chạy |
| 1.3: lịch khách, bàn nhỏ nhất, đầy bàn bỏ lượt | `test_four_seats_fill_on_schedule_and_skip_when_full` | Chưa chạy |
| 2: chỉ món kế hoạch, không quota, kho đã giữ | `test_day_filter_ignores_planned_serving_limit_and_reservations` | Chưa chạy |
| 2: chọn món theo seed, thứ tự ID ổn định | `test_plan_order_does_not_change_seeded_choice` | Chưa chạy |
| 1.3/4.5: hai bếp, đơn cũ, closing dọn món/không giảm uy tín | `test_two_stoves_cook_oldest_then_table_id_and_cleanup`, regression P1 | Chưa chạy |
| Kho sáu loại, lẩu mắm tốn đúng công thức | `test_six_ingredient_inventory_roundtrip_and_new_dish` | Chưa chạy |
| 4.3: fixture ngoài kế hoạch/thiếu kho | `test_invalid_filter_and_day_fixture_rejected` | Chưa chạy |
| Validation dữ liệu | `test_invalid_tuning_rejected` | Chưa chạy |

Test P1 `test_full_table_skips_without_consuming_id` có fixture một bàn
tường minh: preset mới bốn bàn khiến một khách không còn nghĩa là đầy.
Giữ nguyên assertion và mục tiêu kiểm, không thay luật cho test đạt.

Smoke gather→quan sáu nguyên liệu, day một/nhiều ngày và ma trận verification
toàn phase chờ tích hợp các lát; không có output runtime được tạo trong phiên.
