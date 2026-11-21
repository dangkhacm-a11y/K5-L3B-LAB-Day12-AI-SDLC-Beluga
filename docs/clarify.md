# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 | Schema `data` chính xác cho các sự kiện `gather`, `fish_caught`, `hold_full` ở chế độ `gather` là gì? | Giả định tạm: `gather` (`node_id`, `kind`, `count`, `hold_count`), `fish_caught` (`fish_id`, `kind`, `count`, `hold_count`), `hold_full` (`kind`, `hold_count`, `hold_capacity`). Cần PO đối chiếu PRD-0. | Thành viên 2 (chờ PO chốt) |
| 2 | 2026-11-21 | Khi bắt cá có `yield > 1` (ví dụ `ca_linh` = 3) nhưng giỏ chỉ còn 1–2 chỗ trống: nhặt phần vừa chỗ trống hay từ chối toàn bộ? | Giả định tạm: nhặt tối đa chỗ trống (`min(yield, free)`), xóa đàn cá, phát `fish_caught` kèm `hold_full`; nếu giỏ đã đầy 100% (`free == 0`) thì không xóa cá và chỉ phát `hold_full`. Cần PO đối chiếu PRD-0. | Thành viên 2 (chờ PO chốt) |
| 3 | 2026-11-21 | Bấm `catch` dưới nước khi không có cá trong tầm hoặc giỏ đầy có kích hoạt `catch_cd_ticks` không? | Giả định tạm: mọi thao tác bấm `catch` hợp lệ dưới nước khi `catch_cd_ticks == 0` đều đặt lại hồi chiêu `catch_cooldown_s * 60`. Cần PO đối chiếu PRD-0. | Thành viên 2 (chờ PO chốt) |
