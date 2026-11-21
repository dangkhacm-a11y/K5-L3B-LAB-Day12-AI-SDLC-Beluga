# Ma trận truy vết Phase 2 — TICKET-02

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-2/...`) | Kết quả |
|---|---|---|---|
| Gather: tuning đủ ba loài cá, 8 đàn ở các vị trí riêng, N5/N6 và dữ liệu spawn | `load_contract()`; `test_gather_snapshot_has_gather_fields` | [gather-seed1.jsonl](../proof/phase-2/gather-seed1.jsonl), [member-1-fish.txt](../proof/phase-2/member-1-fish.txt) | Đạt trên nhánh Thành viên 1 |
| Cá bơi 1.5 m/s, đổi hướng theo seed mỗi 120 bước, phản xạ biên và fixture tĩnh khi `random_fish:false` | `FishMovementTests` | [member-1-fish.txt](../proof/phase-2/member-1-fish.txt) | Đạt trên nhánh Thành viên 1 |
| Cá sinh sau khi bơi mỗi 360 tick, tối đa 12; bỏ lượt nếu mọi điểm bị chiếm | `FishMovementTests` | [member-1-fish.txt](../proof/phase-2/member-1-fish.txt) | Đạt trên nhánh Thành viên 1 |
| Bắt cá cần đủ chỗ cho cả đàn; hồi 30 tick chỉ sau bắt thành công | `CatchFishTests` | [member-1-fish.txt](../proof/phase-2/member-1-fish.txt) | Đạt trên nhánh Thành viên 1 |
| Cá Sấu, vòng quán, day, Shop, pause/HUD, toàn phase tích hợp | Theo các lát còn lại và smoke tích hợp | Chưa có | Chưa kiểm chứng |
