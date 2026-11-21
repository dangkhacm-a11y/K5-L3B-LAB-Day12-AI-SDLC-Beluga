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
﻿# Ma trận truy vết Phase 2 — TICKET-02
# Ma trận truy vết Phase 2 — TICKET-02

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-2/...`) | Kết quả |
|---|---|---|---|
| Gather: tuning đủ ba loài cá, 8 đàn ở các vị trí riêng, N5/N6 và dữ liệu spawn | `load_contract()`; `test_gather_snapshot_has_gather_fields` | [gather-seed1.jsonl](../proof/phase-2/gather-seed1.jsonl), [member-1-fish.txt](../proof/phase-2/member-1-fish.txt) | Đạt trên nhánh Thành viên 1 |
| Cá bơi 1.5 m/s, đổi hướng theo seed mỗi 120 bước, phản xạ biên và fixture tĩnh khi `random_fish:false` | `FishMovementTests` | [member-1-fish.txt](../proof/phase-2/member-1-fish.txt) | Đạt trên nhánh Thành viên 1 |
| Cá sinh sau khi bơi mỗi 360 tick, tối đa 12; bỏ lượt nếu mọi điểm bị chiếm | `FishMovementTests` | [member-1-fish.txt](../proof/phase-2/member-1-fish.txt) | Đạt trên nhánh Thành viên 1 |
| Bắt cá cần đủ chỗ cho cả đàn; hồi 30 tick chỉ sau bắt thành công | `CatchFishTests` | [member-1-fish.txt](../proof/phase-2/member-1-fish.txt) | Đạt trên nhánh Thành viên 1 |
| Cá Sấu Năm Chèo: tuning `gather.monsters`, quần thể theo ngày (M1 D1, M2 D3), patrol 1.0 m/s, chase 3.0 m/s (`d >= 10`, `<= 10 m`), thoát chase (`> 16 m` hoặc `d < 10`), chặn biên & dải độ sâu | `CrocodileSpawnAndPatrolTests`, `MonsterScenarioValidationTests` | [member-2-monsters.txt](../proof/phase-2/member-2-monsters.txt), [gather-seed1.jsonl](../proof/phase-2/gather-seed1.jsonl) | Đạt |
| Va chạm sau khi di chuyển (`<= 1.5 m`, tối đa 1 hit theo gần nhất rồi `id`), mất 1 HP, rơi `floor(hold/2)` LIFO, bất tử 90 tick, recoil 60 bước `2/60 m` từ bước kế | `CrocodileHitRecoilInvulnFaintTests` | [member-2-monsters.txt](../proof/phase-2/member-2-monsters.txt) | Đạt |
| Hit gây ngất phát `faint` (`cause:"monster"`, `lost` phần còn lại, `hp:0`) + `gather_end(fainted)` kho rỗng; ngạt xuyên bất tử không rơi hàng, thứ tự tick mục 4.5 | `CrocodileHitRecoilInvulnFaintTests`, `MonsterScenarioValidationTests` | [member-2-monsters.txt](../proof/phase-2/member-2-monsters.txt) | Đạt |
| Mở rộng Lao xua (`extensions: ["weapon"]`): phím `Q` (`attack`), cần cấp 1, hồi 180 tick kể cả trượt, cấp 1 (4m / 120 bước) & cấp 2 (6m / 180 bước) kể cả bước bị Lao, đẩy 3m theo `id`, ghi đè recoil/choáng, event `attack`/`monster_stunned` | `WeaponExtensionTests`, `test_smoke_p1.py` | [member-2-monsters.txt](../proof/phase-2/member-2-monsters.txt) | Đạt |
| Vòng quán, day, Shop, pause/HUD, toàn phase tích hợp | Theo các lát còn lại và smoke tích hợp | Chưa có | Chưa kiểm chứng |
