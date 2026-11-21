# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 4 | 2026-11-21 | Schema khách/món, event no_dish, thứ tự tick và đóng ca Quán? | Đã có PRD đầy đủ từ người dùng: state tách order_status, món `{order_id,dish_id,base_price}`, no_dish `{}`, quyết toán sau interact theo ID bàn, closing không trừ uy tín khách chờ. Đối chiếu `docs/plan/member-3-restaurant.md`. | Người dùng / PRD-0 D–F |
| 5 | 2026-11-21 | Phase 2: số suất trong kế hoạch có chặn khách gọi tiếp? | Không. TICKET-02 mục 2: chỉ dùng để tính mục tiêu thu gom; Quán lọc theo ID món trong kế hoạch rồi theo kho chưa giữ. Quán độc lập dùng đủ sáu món. API bàn giao `allowed_dishes=day_plan["dishes"]`; lát 4 kiểm số suất/kế hoạch và giữ tiền/uy tín. | Người dùng / TICKET-02 |
| 1 | 2026-11-21 | Schema `data` chính xác cho các sự kiện `gather`, `fish_caught`, `hold_full` ở chế độ `gather` là gì? | Giả định tạm: `gather` (`node_id`, `kind`, `count`, `hold_count`), `fish_caught` (`fish_id`, `kind`, `count`, `hold_count`), `hold_full` (`kind`, `hold_count`, `hold_capacity`). Cần PO đối chiếu PRD-0. | Thành viên 2 (chờ PO chốt) |
| 2 | 2026-11-21 | Khi bắt cá có `yield > 1` nhưng giỏ không đủ chỗ cho cả đàn thì xử lý thế nào? | TICKET-02 §1.1 chốt: không bắt/xóa đàn, không thêm một phần; phát `hold_full`. | TICKET-02 |
| 3 | 2026-11-21 | Khi nào thao tác bắt cá đặt `catch_cd_ticks`? | TICKET-02 §1.1 chốt: chỉ lần bắt thành công mới bắt đầu hồi chiêu 30 tick; không có cá trong tầm hoặc giỏ không đủ chỗ thì không hồi. | TICKET-02 |

## Phase 3 � th�nh vi�n 1 (2026-11-21)

- Ngu?i d�ng ch?t gi? d?nh d�ng lu: ch?n ng?u nhi�n hu?ng `-1` ho?c `+1` qua `Streams`; ph�t `current_warning` tru?c khi b?t d?u; khi d? s�u d?t `min_depth`, c?ng `direction * speed` v�o v?n t?c ngang. `random_current:false` t?t chu k?, c�n `current_direction` c? d?nh hu?ng cho fixture.
- L?ch m?c d?nh do `gather.current` trong contract v1.2 cung c?p. Gather snapshot c� `current:null` ho?c `{direction,ticks_left}`; `gather_end.data.inventory` d�ng `{items:[{id,kind,fresh}]}` theo th? t? v�o gi?.
- Interface d� tri?n khai tru?c adapter v1.2; vi?c d?c/ghi scenario v� file kho thu?c Th�nh vi�n 3.
