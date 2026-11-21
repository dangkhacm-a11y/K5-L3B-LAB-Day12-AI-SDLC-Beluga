# Ma trận truy vết Phase 2

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-2/...`) | Kết quả (đạt / chưa đạt — ghi trung thực) |
|---|---|---|---|
| **AC-DAY-01** (Vòng ngày & FSM) | Quản lý chuyển phase `gather -> quan -> shop`, bàn giao kho và dọn kho dư sau shop | [unittest.txt](docs/proof/phase-2/unittest.txt) (`test_day_full_cycle_gather_quan_shop_e2e`) | Đạt |
| **AC-DAY-02** (Kế hoạch ngày D1–D5) | Phát `day_plan` với danh sách món & nguyên liệu D1–D5, quán giới hạn thực đơn theo kế hoạch ngày | [unittest.txt](docs/proof/phase-2/unittest.txt) (`test_day_initial_events_and_plan`) | Đạt |
| **AC-DAY-03** (Shop & Nâng cấp) | Mua nâng cấp oxygen & hp, trừ tiền, validate funds/max_level/unknown, kích hoạt `active_upgrades` ở ngày sau | [unittest.txt](docs/proof/phase-2/unittest.txt) (`test_shop_buy_oxygen_and_hp`, `test_day_to_day_progression_and_active_upgrades`) | Đạt |
| **AC-DAY-04** (Tạm dừng Pause) | Nhấn nút `pause` đóng băng mô phỏng (`state: "paused"`), nhấn lại tiếp tục chạy (`state: "playing"`) | [unittest.txt](docs/proof/phase-2/unittest.txt) (`test_day_pause_and_resume`) | Đạt |
| **AC-DAY-05** (Headless Day Contract v1.1) | Chạy headless `--mode day --days 1` mô phỏng trọn ngày 22.200 ticks, định dạng JSONL theo Test Contract v1.1 | [day_days1.jsonl](docs/proof/phase-2/day_days1.jsonl), [unittest.txt](docs/proof/phase-2/unittest.txt) (`test_headless_day_mode_run`) | Đạt |
| **AC-TUNING-01** (Số liệu chuẩn Contract v1.1) | Bổ sung 3 món mới (`canh_chua_ca_loc`, `ca_keo_nuong`, `lau_mam`), 2 nguyên liệu mới (`ca_keo`, `keo_neo`), tuning `day_plan` & `shop` | [game.contract.json](../../game.contract.json), [gather_seed1.jsonl](docs/proof/phase-2/gather_seed1.jsonl), [quan_seed1.jsonl](docs/proof/phase-2/quan_seed1.jsonl) | Đạt |

## Đánh giá ngắn
- **Yêu cầu đã đạt:**
  - Hoàn thành đầy đủ điều phối vòng ngày (`DaySim`), tích hợp chuyển pha liền mạch giữa Lặn & Hái, Quán và Shop.
  - Cài đặt hệ thống Shop nâng cấp (bình oxy, máu) và cơ chế hoãn hiệu lực nâng cấp (`active_upgrades`) sang ngày tiếp theo.
  - Hỗ trợ cơ chế Pause/Resume không trôi thời gian mô phỏng.
  - Tích hợp cờ `--mode day --days <1..5>` trên CLI `headless.py`, đảm bảo toàn bộ 78/78 test kiểm thử tự động xanh hoàn toàn và không phát sinh hồi quy.
- **Điều cần chuẩn bị cho Phase 3:**
  - Chuẩn bị cơ chế chiến đấu/xua đuổi Cá Sấu Năm Chèo (`attack`, `photo`) theo mở rộng Phase 3.
  - Tích hợp thêm các kịch bản sự kiện ngẫu nhiên trên sông và mở rộng nội thất quán nếu có yêu cầu.
