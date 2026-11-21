# KhiemNTK — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm:**
  - **Phase 1 & 2**: Lát 4 Quán (bếp, bàn, thanh toán), điều phối Vòng ngày (`DaySim`), Shop nâng cấp, Pause/Resume, CLI `--mode day` Test Contract v1.1.
  - **Phase 3**: Thiết kế HUD 2D Canvas sông nước Nam Bộ (độ tươi cá thể, dòng lũ, đặt trước), tích hợp bàn giao kho an toàn.
  - **Phase 4**: Lập biên bản hồi tưởng `docs/retro.md`, điều phối kiểm chứng regression P1–P4, chuẩn bị phát hành tag `phase-4` và Release `v1.0.0`.
- **Tôi đã review & hỗ trợ:**
  - Review hợp đồng kho v1.2/v1.3, hỗ trợ gỡ xung đột merge `runner.py`/`headless.py`, bảo đảm tính tất định của headless runner.
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - AI giả định kho luôn là dictionary và kích hoạt nâng cấp shop ngay trong ngày; tôi phát hiện qua traceback unit test và đối chiếu PRD để sửa logic tách biệt trạng thái.
- **Điều tôi học được:**
  - Kiến trúc phân lớp rõ ràng (sim, runner, adapter, UI) cùng tư duy kiểm thử tự động giúp dự án quy mô nhiều thành viên tích hợp nhanh, không nợ kỹ thuật.
