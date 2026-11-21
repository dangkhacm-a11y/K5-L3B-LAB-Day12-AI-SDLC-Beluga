# tad-4963 (Trần Anh Dũng — 04037) — phản tư cá nhân (≤ 200 từ)

- **Đã làm:**
  - **P1** (`f08aea4`, `1cdb86c`, `397442f`): Gather lát 2 — hái nút, mọc lại, bắt cá, giỏ đầy, ưu tiên cập bến và xuất kho.
  - **P2** (`8130e49`, `eb1270c`, `90bbb39`): Cá Sấu (`patrol`/`chase`, va chạm, rơi LIFO, bất tử 90 tick, `recoil` 60 bước, `faint`) và mở rộng Lao xua (`weapon`).
  - **P3** (`9673087`, `8bf477b`, `b32a68d`): Quán v1.2 — kho cá thể, độ tươi `Fraction`, `spoiled`, giữ chỗ theo ID, chốt giá và `reservations`.
  - **P4**: HUD 3 cảnh báo, tương phản cao, phụ đề SFX khi tắt tiếng và sprite Kenney CC0 (`tests/test_ui_alerts_p4.py`, `docs/proof/phase-4/member-2-ui-alerts.txt`).
- **Hỗ trợ / review:** Chốt thứ tự tick Gather với `dangkhacm-a11y`, gỡ xung đột `contract.py` (`7200018`) với `DanielHa01`, phát hiện thiếu `Session.tick` ở `runner.py`.
- **AI sai & phát hiện:** P1 AI giả định partial fill cho `ca_linh`; đối chiếu TICKET-02 §1.1 đã sửa. P2 `edit_file` chèn trùng vẽ cá sấu sang `drawQuan`; phát hiện qua log diff và xóa ngay.
- **Bài học:** Khóa hợp đồng sớm và chạy test hồi quy sau mỗi merge giúp `main` ổn định.
