# KhiemNTK — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm:**
  - Nhận trách nhiệm Thành viên 4: Quán (Bếp, bàn, thanh toán, boa, uy tín, kết ca) và Tích hợp hệ thống Phase 1.
  - Cài đặt toàn bộ logic tương tác tại bếp (`cook_started`, `dish_ready`, `dish_picked`) và tại bàn (`served`, `eating`, `paid`).
  - Viết bộ unit test `tests/test_quan_member4.py` và integration test E2E `tests/test_integration_gather_quan.py`.
  - Thực hiện kiểm chứng ma trận Phase 1, xuất log và bằng chứng JSONL tại `docs/proof/phase-1/`.
- **Tôi đã review:**
  - Review hợp đồng kho `docs/contracts/` và logic giao tiếp giữa `GatherSim` và `QuanSim`.
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - Khi chạy trên Windows, lệnh `python3` trong `game.contract.json` gọi vào stub của Microsoft Store (mã lỗi 9009) thay vì `python.exe` thật. Tôi phát hiện qua traceback của subprocess và đã tạo wrapper/alias xử lý triệt để.
- **Điều tôi học được:**
  - Giữ code tinh gọn, dùng trực tiếp thư viện chuẩn Python thay vì thêm dependencies phức tạp giúp code chạy nhanh, dễ kiểm thử và không có nợ kỹ thuật.
