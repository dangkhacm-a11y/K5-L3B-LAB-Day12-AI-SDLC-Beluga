# KhiemNTK — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm:**
  - **Phase 1**: Quán (bếp, bàn, thanh toán, boa, uy tín), test `test_quan_member4.py` và E2E liên thông kho.
  - **Phase 2**: Vòng ngày `DaySim`, Shop (`oxygen`, `hp`), Pause/Resume, CLI `--mode day` v1.1.
  - **Phase 3**: Nâng cấp HUD sông nước Nam Bộ (`index.html`, `live.py`) hiển thị độ tươi, hàng ươn, dòng lũ và đơn đặt trước `reservations`; tích hợp bàn giao kho cá thể Phase 3 cho `DaySim`.
- **Tôi đã review:**
  - Hợp đồng kho cá thể v1.2, tính tất định của headless runner và tính tương thích giữa các pha.
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - AI giả định kho luôn là dictionary đếm số lượng, gây crash khi Phase 3 đổi sang danh sách cá thể `{id, kind, fresh}`. Tôi phát hiện qua traceback test và cập nhật adapter an toàn cho cả hai schema.
- **Điều tôi học được:**
  - Thiết kế adapter bao bọc schema tốt giúp hệ thống vừa mở rộng tính năng mới vừa không phá vỡ tính tương thích ngược.
