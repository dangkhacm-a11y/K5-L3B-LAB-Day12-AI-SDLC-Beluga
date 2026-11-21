# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 | Schema `data` chính xác cho các sự kiện `gather`, `fish_caught`, `hold_full` ở chế độ `gather` là gì? | Giả định tạm: `gather` (`node_id`, `kind`, `count`, `hold_count`), `fish_caught` (`fish_id`, `kind`, `count`, `hold_count`), `hold_full` (`kind`, `hold_count`, `hold_capacity`). Cần PO đối chiếu PRD-0. | Thành viên 2 (chờ PO chốt) |
| 2 | 2026-11-21 | Khi bắt cá có `yield > 1` nhưng giỏ không đủ chỗ cho cả đàn thì xử lý thế nào? | TICKET-02 §1.1 chốt: không bắt/xóa đàn, không thêm một phần; phát `hold_full`. | TICKET-02 |
| 3 | 2026-11-21 | Khi nào thao tác bắt cá đặt `catch_cd_ticks`? | TICKET-02 §1.1 chốt: chỉ lần bắt thành công mới bắt đầu hồi chiêu 30 tick; không có cá trong tầm hoặc giỏ không đủ chỗ thì không hồi. | TICKET-02 |
