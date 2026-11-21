# Ma trận truy vết Phase 3 — TICKET-03

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-3/...`) | Kết quả |
|---|---|---|---|
| Quán v1.2: Kho cá thể `{id,kind,fresh}`, hao tươi `0.25/s` (`1/240`/tick chính xác), phát `spoiled` theo `id` khi qua ngưỡng `< 30` | `QuanFreshnessAndPricingTests` trong `tests/test_quan_phase3.py` | [member-2-quan.txt](../proof/phase-3/member-2-quan.txt) | Đạt |
| Quán v1.2: Giữ chỗ theo ID chọn cá thể tươi nhất hòa theo `id`, thử giữ lại theo `(order_tick, table_id)` khi hàng vừa ươn, chốt `base_price` theo độ tươi và sắp `cook_started.items` theo `(kind, id)` | `QuanFreshnessAndPricingTests` trong `tests/test_quan_phase3.py` | [member-2-quan.txt](../proof/phase-3/member-2-quan.txt) | Đạt |
| Quán v1.2: Vòng đời `reservations` (`scheduled → holding → waiting → served\|failed`), giữ bàn trước 30s, giá cuối `floor(base_price × 1.5)` trước khi tính boa, fail `occupied`/`stock`/`burnt`/`patience`/`closing` không phạt lặp | `QuanReservationsTests` trong `tests/test_quan_phase3.py` | [member-2-quan.txt](../proof/phase-3/member-2-quan.txt) | Đạt |
| **AC-HUD-01** (HUD Gather v1.2) | Hiển thị giỏ cá thể, thanh độ tươi `fresh`, cảnh báo ươn (< 30), dòng lũ cuộn (`current`), cá sấu M1/M2 | [index.html](../../chonoi/web/index.html), [live.py](../../chonoi/live.py) | Đạt |
| **AC-HUD-02** (HUD Quán v1.2) | Hiển thị kho tổng hợp cá thể, danh sách đơn đặt trước (`reservations` R1/R2), biển đặt chỗ trên bàn ăn | [index.html](../../chonoi/web/index.html), [live.py](../../chonoi/live.py) | Đạt |
| **AC-INT-03** (Vòng ngày tích hợp Phase 3) | `DaySim` bàn giao giỏ cá thể `{id, kind, fresh}` sang Quán, hỗ trợ item_mode, dọn kho sau shop | [member-4-day.txt](../proof/phase-3/member-4-day.txt) (`test_day_full_cycle_gather_quan_shop_e2e`) | Đạt |
| Adapter kho v1.2 (`game.contract.json`, `inventory.py`, `scenario.py`, `contract.py`), Gather độ tươi/dòng lũ, HUD & tích hợp toàn phase | Các lát Thành viên 1, 3, 4 và smoke tích hợp | [member-4-day.txt](../proof/phase-3/member-4-day.txt) | Đang hoàn tất |
