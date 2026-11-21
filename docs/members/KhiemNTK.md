# KhiemNTK — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm:**
  - **Phase 1**: Nhận Lát 4 Quán (bếp, bàn, thanh toán, boa, uy tín, kết ca), viết unit test `test_quan_member4.py` và integration test E2E `test_integration_gather_quan.py`.
  - **Phase 2**: Cài đặt điều phối vòng ngày (`DaySim`), FSM chuyển pha, hệ thống Shop nâng cấp (`oxygen`, `hp`), cơ chế Pause/Resume và cờ CLI `--mode day --days <1..5>` v1.1. Viết bộ kiểm thử `test_day_member4.py` và xuất đầy đủ proof Phase 2.
- **Tôi đã review:**
  - Hợp đồng Test Contract v1.1 (`game.contract.json`), sơ đồ kho liên thông và tính tất định của headless runner.
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - AI khởi tạo nâng cấp kích hoạt ngay trong ngày hiện tại; tôi phát hiện qua spec TICKET-02 (nâng cấp mua ở Shop chỉ áp dụng từ ngày hôm sau) và đã tách thành `upgrades` và `active_upgrades`.
- **Điều tôi học được:**
  - Tách bạch state giữa các phase và quản lý vòng đời FSM rõ ràng giúp tích hợp mượt mà, giữ vững tính tất định 100% qua hàng chục nghìn tick.
