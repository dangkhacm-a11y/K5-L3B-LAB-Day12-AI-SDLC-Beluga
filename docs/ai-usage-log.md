# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| Phase 1 | Thành viên 3 (chưa khai handle) | Codex | Luật khách/giữ chỗ/kiên nhẫn, tích hợp lát 4 theo PRD, UI Quán và test | Không đo được | Lần đầu dừng ở baseline, bản tạm dùng sai schema; đã đổi theo PRD người dùng cung cấp. Checkout được cập nhật trong phiên nên tích hợp lại trên d67330a. Review phát hiện lỗi score do số thực và UI input/live-region; có regression checks. |
| Phase 1 | KhiemNTK | Antigravity (Gemini 3.8 Flash High) | Thiết kế Lát 4 Quán (bếp, bàn, thanh toán), viết test TDD & kiểm chứng tích hợp E2E | ~25k tokens | Cần chú ý tương thích Windows alias python3 vs python trong subprocess test |
