# Ma trận truy vết Phase 3 — TICKET-03

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-3/...`) | Kết quả |
|---|---|---|---|
| Quán v1.2: Kho cá thể `{id,kind,fresh}`, hao tươi `0.25/s` (`1/240`/tick chính xác), phát `spoiled` theo `id` khi qua ngưỡng `< 30` | `QuanFreshnessAndPricingTests` trong `tests/test_quan_phase3.py` | [member-2-quan.txt](../proof/phase-3/member-2-quan.txt) | Đạt |
| Quán v1.2: Giữ chỗ theo ID chọn cá thể tươi nhất hòa theo `id`, thử giữ lại theo `(order_tick, table_id)` khi hàng vừa ươn, chốt `base_price` theo độ tươi và sắp `cook_started.items` theo `(kind, id)` | `QuanFreshnessAndPricingTests` trong `tests/test_quan_phase3.py` | [member-2-quan.txt](../proof/phase-3/member-2-quan.txt) | Đạt |
| Quán v1.2: Vòng đời `reservations` (`scheduled → holding → waiting → served\|failed`), giữ bàn trước 30s, giá cuối `floor(base_price × 1.5)` trước khi tính boa, fail `occupied`/`stock`/`burnt`/`patience`/`closing` không phạt lặp | `QuanReservationsTests` trong `tests/test_quan_phase3.py` | [member-2-quan.txt](../proof/phase-3/member-2-quan.txt) | Đạt |
| Adapter kho v1.2 (`game.contract.json`, `inventory.py`, `scenario.py`, `contract.py`), Gather độ tươi/dòng lũ, HUD & tích hợp toàn phase | Các lát Thành viên 1, 3, 4 và smoke tích hợp | Chưa có | Chưa kiểm chứng |
