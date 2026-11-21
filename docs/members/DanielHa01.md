# DanielHa01 — Báo cáo cá nhân

- **Tôi đã làm (kèm commit/bằng chứng):** 
Phase 1: triển khai khách đến, giữ nguyên liệu, thời gian chờ và ghép luồng nấu, phục vụ, thanh toán ([d90ae98](https://github.com/dangkhacm-a11y/K5-L3B-LAB-Day12-AI-SDLC-Beluga/commit/d90ae98)). 
Phase 2: cập nhật hai bếp, bốn bàn, sáu món và lọc menu theo kế hoạch ngày ([29f2c87](https://github.com/dangkhacm-a11y/K5-L3B-LAB-Day12-AI-SDLC-Beluga/commit/29f2c87)). Phase 3: sửa lưu kho, chuyển Gather sang Quán và lỗi hiển thị giỏ cá thể ([419eb19](https://github.com/dangkhacm-a11y/K5-L3B-LAB-Day12-AI-SDLC-Beluga/commit/419eb19), [ff463a4](https://github.com/dangkhacm-a11y/K5-L3B-LAB-Day12-AI-SDLC-Beluga/commit/ff463a4)).
Phase 4: rà soát lại các file report và viết report cá nhân
- **Tôi đã rà soát:** Kiểm tra kho khi chuyển màn, giữ ID và độ tươi sau khi ghép code, đối chiếu kết quả unittest và kiểm tra giao diện bằng Chrome trong [bằng chứng sửa giỏ](../proof/gather-basket-fix.md).
- **AI sai và cách phát hiện:** Bản Quán đầu tiên dùng sai schema. Khi đối chiếu PRD, trạng thái khách và đơn hàng cần tách riêng, nên yêu cầu sửa lại trước khi tích hợp ([nhật ký](../ai-usage-log.md)).
- **Điều em học được:** cần đọc kỹ yêu cầu và kiểm tra dữ liệu giữa các module. Code chạy được chưa đủ, sửa xong vẫn phải thử các trường hợp dễ lỗi.
