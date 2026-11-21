# Ma trận truy vết Phase 1

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-1/...`) | Kết quả (đạt / chưa đạt — ghi trung thực) |
|---|---|---|---|
| Gather lát 2: Hái nút ở mặt nước, chọn gần nhất (tie-break theo id nhỏ), mọc lại `node_regrown` | Unit test `GatherNodeTests` trong `tests/test_gather_harvest.py` | [member-2-tests.txt](../proof/phase-1/member-2-tests.txt) | Đạt (chờ PO xác nhận payload event trong `docs/clarify.md`) |
| Gather lát 2: Bắt cá dưới nước bằng `catch`, hồi chiêu `catch_cd_ticks`, tie-break theo id | Unit test `CatchFishTests` trong `tests/test_gather_harvest.py` | [member-2-tests.txt](../proof/phase-1/member-2-tests.txt) | Đạt (chờ PO xác nhận luật partial fill & cooldown trong `docs/clarify.md`) |
| Gather lát 2: Xử lý giỏ đầy `hold_full`, ưu tiên cập bến trước hái, xuất kho qua headless | Unit + headless test `GatherHeadlessInventoryTests`, `test_smoke_p1.py`, `gather-seed1.jsonl` | [member-2-tests.txt](../proof/phase-1/member-2-tests.txt), [gather-seed1.jsonl](../proof/phase-1/gather-seed1.jsonl) | Đạt |

## Đánh giá ngắn
- Yêu cầu nào đạt / chưa đạt:
- Điều cần chỉnh cho phase sau:
