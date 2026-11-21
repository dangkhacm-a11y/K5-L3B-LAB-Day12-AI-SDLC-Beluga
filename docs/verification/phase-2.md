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
