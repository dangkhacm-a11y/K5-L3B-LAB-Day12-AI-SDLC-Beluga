# Ma trận truy vết Phase 1

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-1/...`) | Kết quả (đạt / chưa đạt — ghi trung thực) |
|---|---|---|---|
| **AC-QUAN-01** (Bếp nhận nấu) | Tương tác bếp idle khi đủ nguyên liệu, trừ kho và phát `cook_started` | [unittest.txt](docs/proof/phase-1/unittest.txt) (`test_cook_started_and_dish_ready`) | Đạt |
| **AC-QUAN-02** (Món chín) | Đếm ngược `cook_ticks_left`, khi về 0 chuyển `ready` và phát `dish_ready` | [unittest.txt](docs/proof/phase-1/unittest.txt) (`test_cook_started_and_dish_ready`) | Đạt |
| **AC-QUAN-03** (Lấy món) | Tương tác bếp ready khi tay trống, bốc món lên `hand` (`dish_picked`), bếp về `idle` | [unittest.txt](docs/proof/phase-1/unittest.txt) (`test_dish_picked`) | Đạt |
| **AC-QUAN-04** (Phục vụ) | Cầm đúng món tương tác bàn khách chờ, giao món (`served`), khách chuyển sang `eating` | [unittest.txt](docs/proof/phase-1/unittest.txt) (`test_served_and_paid_with_tip`) | Đạt |
| **AC-QUAN-05** (Thanh toán & Tip) | Khách ăn đủ `eat_s`, trả tiền (`paid`), nhận boa 20% và tăng uy tín nếu kiên nhẫn >= 50% | [unittest.txt](docs/proof/phase-1/unittest.txt) (`test_served_and_paid_with_tip`, `test_paid_without_tip_when_patience_low`) | Đạt |
| **AC-QUAN-06** (Ưu tiên interact) | Khoảng cách gần nhất -> Bếp trước bàn -> ID nhỏ trước | [unittest.txt](docs/proof/phase-1/unittest.txt) (`test_interact_priority_distance_and_stove_first`) | Đạt |
| **AC-INT-01** (Liên thông kho E2E) | Gather xuất kho qua `--inventory-out`, Quán nạp qua `--inventory` và nấu món thành công | [unittest.txt](docs/proof/phase-1/unittest.txt) (`test_gather_inventory_to_quan_cooking_e2e`) | Đạt |
| **AC-HEADLESS-01** (Headless Gather 600t) | Chạy mô phỏng gather 600 ticks tất định | [gather_seed1.jsonl](docs/proof/phase-1/gather_seed1.jsonl) | Đạt |
| **AC-HEADLESS-02** (Headless Quán 600t) | Chạy mô phỏng quan 600 ticks tất định | [quan_seed1.jsonl](docs/proof/phase-1/quan_seed1.jsonl) | Đạt |

## Đánh giá ngắn
- **Yêu cầu đã đạt:**
  - Hoàn thành đầy đủ toàn bộ logic Lát 4 cho chế độ Quán (`chonoi/sim/quan.py`).
  - Kiểm thử 38/38 unit test & integration test xanh hoàn toàn.
  - Tích hợp liên thông kho Gather -> Quán thành công.
- **Điều cần chỉnh cho phase sau:**
  - Phối hợp với Thành viên 3 để ghép nối logic lịch sinh khách ngẫu nhiên (`random_customers`) và di chuyển khách vào/ra quán trực quan hơn.
  - Mở rộng xử lý khi cháy món (`burn_s`) nếu các phase sau kích hoạt.
