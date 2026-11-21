# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| Phase 1 | DanielHa01 | Codex | Luật khách/giữ chỗ/kiên nhẫn, tích hợp lát 4 theo PRD, UI Quán và test | Không đo được | Lần đầu dừng ở baseline, bản tạm dùng sai schema; đã đổi theo PRD người dùng cung cấp. Checkout được cập nhật trong phiên nên tích hợp lại trên d67330a. Review phát hiện lỗi score do số thực và UI input/live-region; có regression checks. |
| Phase 1 | KhiemNTK | Antigravity (Gemini 3.8 Flash High) | Thiết kế Lát 4 Quán (bếp, bàn, thanh toán), viết test TDD & kiểm chứng tích hợp E2E | ~25k tokens | Cần chú ý tương thích Windows alias python3 vs python trong subprocess test |
| Phase 2 | KhiemNTK | Antigravity (Gemini 3.8 Flash High) | Thiết kế DaySim FSM, Shop upgrades, Pause mechanism, CLI --mode day contract v1.1 | ~35k tokens | Nâng cấp shop ban đầu bị nhầm áp dụng ngay trong ngày thay vì sang ngày hôm sau; đã sửa lại tách `active_upgrades` |
| Phase 2 | DanielHa01 | Codex | Đọc Task/TICKET-02; dữ liệu 2 bếp/4 bàn/6 món, hai nguyên liệu mới, lọc menu theo kế hoạch ngày, validation và test bàn giao | Không đo được | Manifest version và điều phối day do lát 1/4 tích hợp. |
| Phase 3 | KhiemNTK | Antigravity (Gemini 3.8 Flash High) | Thiết kế HUD/UI sông nước miền Tây, hỗ trợ cá thể freshness, current, reservations; tích hợp DaySim Phase 3 | ~40k tokens | Adapter kho ban đầu chỉ nhận dict gây crash khi nhận mảng cá thể; đã sửa hỗ trợ cả 2 schema |