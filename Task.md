# Phân công nhóm — Phase 3 (TICKET-03)

> Phạm vi ưu tiên: lõi Test Contract v1.2 trong 35 phút (1:55–2:30). `TEAM.md` chưa có tên/handle, nên tạm dùng Thành viên 1–4. Điền tên và vai trò lúc kickoff. Chưa nhận mở rộng nếu schema, độ tươi, đơn đặt trước và smoke chưa đạt.

## Thành viên 1 — Gather: độ tươi, mã cá thể và dòng lũ

- **Phạm vi:** `chonoi/sim/gather.py` và test Gather; phối hợp interface với chủ sở hữu kho trước khi sửa.
- Chuyển giỏ sang danh sách cá thể `{id, kind, fresh}`. Mỗi lần hái/bắt thành công cấp ID `I1`, `I2`… theo thứ tự vào giỏ; dùng chung bộ cấp ID xuyên pha/Ngày, không tái sử dụng ID đã dùng hoặc bỏ.
- Mỗi tick Gather giảm freshness theo `freshness.gather_decay_per_s`; phát `spoiled` theo ID khi freshness xuống dưới `spoiled_below`, không giữ cá thể ươn trong giỏ. Hái/bắt tạo cá thể với freshness ban đầu theo contract.
- `lost`/`faint`/hit làm mất hàng theo LIFO và giữ đúng thứ tự cá thể; ngất bỏ toàn bộ phần còn lại, bàn giao kho rỗng.
- Cài lịch dòng lũ theo `gather.current`: trạng thái/snapshot, tác động dòng theo độ sâu, cảnh báo và fixture `random_current:false`/`current_direction` theo ticket. Phối hợp Thành viên 4 về HUD và Integrator về tick chuyển pha.
- **Bàn giao:** unit test độ tươi qua ngưỡng 30, event tick chính xác, ID/LIFO, hướng dòng và fixture tắt lịch; bằng chứng tại `docs/proof/phase-3/member-1-gather.*`.

## Thành viên 2 — Quán: độ tươi, đặt món và đơn đặt trước

- **Phạm vi:** `chonoi/sim/quan.py` và test Quán; đây là chủ sở hữu duy nhất của luật trong module này.
- Kho quán và `customers[].reserved` dùng cá thể theo ID. Mỗi tick Quán giảm freshness theo `freshness.quan_decay_per_s`; phát `spoiled` theo ID/location, bỏ hàng ươn và thử giữ lại đơn theo đúng thứ tự `order_tick`, rồi `table_id`.
- Thực hiện chọn cá thể tươi nhất, hòa theo ID; chốt `base_price` khi giữ món và tính giá cuối `floor(base_price × reservations.price_multiplier)` trước khi tính boa.
- Cài vòng đời reservation `scheduled → holding → waiting → served|failed`: giữ bàn trước giờ đến, chọn món theo kế hoạch trong `day`/đủ menu ở `quan`, giữ nguyên liệu, phục vụ, tính giá/boa; xử lý fail `occupied`, `stock`, `burnt`, `patience`, `closing`, nhả bàn/nguyên liệu và trừ uy tín đúng một lần.
- **Bàn giao:** test các nhánh biên tại `spoiled_below`, giờ đến/giờ đóng ca, món cháy nếu bật, giá/boa, không phạt lặp; bằng chứng Quán Phase 3.

## Thành viên 3 — Hợp đồng kho cá thể và chuyển dữ liệu

- **Phạm vi:** chủ sở hữu duy nhất của `game.contract.json`, `chonoi/inventory.py`, validation trong `chonoi/contract.py`/`chonoi/scenario.py`, adapter file kho và bộ cấp ID cá thể dùng chung.
- Nâng manifest lên `contract_version: 1.2`; thêm `freshness`, `gather.current`, `reservations` và kiểm tra dải/schema theo ticket. Kho file v1.2 chỉ nhận `{"items":[{"id","kind","fresh"}]}`; từ chối kho đếm v1.0/1.1, ID trùng/rỗng, kind lạ, fresh không hữu hạn hoặc ngoài `[0,100]` bằng mã 2.
- Cập nhật scenario: `gather.hold`, `quan.stock`, `customers[].reserved`, `quan.reservations[]`, cờ tắt ngẫu nhiên và bộ kiểm mâu thuẫn/ID dùng đồng thời. Giữ độ chính xác freshness khi serialize/đọc lại và ghi file nguyên tử đúng một lần sau `gather_end`; hết tick trước kết thúc không đụng file đích.
- Chốt adapter/API cá thể dùng chung cho Thành viên 1–2 trước khi họ tích hợp. Xử lý cấp ID liên tục qua ngày, hàng Shop chờ nhập, hàng nhập có `fresh:100`; ID duy nhất giữa mọi nơi chứa.
- **Bàn giao:** test schema cũ bị từ chối, kho rỗng, migration/round-trip, precision quanh ngưỡng 30, ghi file và xung đột scenario.

## Thành viên 4 — HUD, luồng hiển thị và tích hợp/release

- **Phạm vi:** `chonoi/web/`, `chonoi/live.py`/client, smoke integration, tài liệu và release; tránh sửa luật `gather.py`/`quan.py`/adapter nếu chưa phối hợp với chủ sở hữu.
- Hiển thị độ tươi/hàng ươn trong HUD Gather và Quán; hiển thị trạng thái/giờ đến/bàn của R1/R2; dòng lũ và cảnh báo. Không thay logic mô phỏng trong UI.
- Ghép theo thứ tự adapter → Gather/Quán → UI; kiểm tra bàn giao trong cùng tick ở `day` không hao freshness thêm, kho `gather_end` đúng, Shop nhập hàng riêng với ID mới.
- Chạy smoke kho qua file và trong `day`; chạy regression P1–P2 còn hiệu lực; lưu bằng chứng, cập nhật `docs/verification/phase-3.md`, `CHANGELOG.md`, `docs/clarify.md`, `docs/ai-usage-log.md`, retro. Gắn tag `phase-3` lên đúng commit `main` trước 2:30.
- **Bàn giao:** PR/tích hợp có bằng chứng, không ghi đạt cho nhánh chưa chạy.

## Thứ tự phối hợp và điểm cần PO chốt

1. **Phút 0–7:** Integrator (khuyến nghị Thành viên 4) chốt API kho với Thành viên 3 và hai chủ module; ghi breaking change, thứ tự tích hợp, chủ sở hữu file và quyết định vào `docs/clarify.md`/`CHANGELOG.md`. Mọi người thống nhất item `{id,kind,fresh}` và cấp ID `I…` trước khi code song song.
2. **Adapter trước:** Thành viên 3 đưa schema/API, kiểm validation và fixture migration lên nhánh tích hợp; Thành viên 1–2 viết luật theo API đã chốt. Không để manifest v1.2 chạy cùng adapter kho đếm cũ.
3. **Phút 20:** smoke Gather một tick qua ngưỡng, ghi inventory file, nạp vào Quán với `--ticks 0`; so ID/kind/fresh. Sau đó smoke chuyển pha `day` trong cùng tick và cập nhật standup.
4. **Phút 20–30:** ghép luật Quán/reservation và HUD; điều người đã xong sang lỗi tích hợp/test đang đỏ.
5. **Phút 30–35:** chạy regression P1–P2 còn phù hợp, smoke ngày, ghi verification/proof, chốt `main` và tag `phase-3` trước 2:30.

Các câu ticket chưa quy định payload/event chi tiết (đặc biệt event cảnh báo/hết dòng lũ, và payload reservation khi hủy giữ nguyên liệu) phải được PO ghi quyết định trong `docs/clarify.md` trước khi module phát event; không tự bịa tên/payload.

## Kiểm chứng chung

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --out gather.jsonl
python3 -m chonoi.headless --mode quan --seed 1 --ticks 600 --out quan.jsonl
python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day.jsonl
```

Thêm smoke kho file v1.2 (bao gồm kho cũ trả mã 2) và fixture freshness 30→dưới 30. Ghi commit chạy, lệnh, kết quả và link bằng chứng trong `docs/verification/phase-3.md`; cập nhật fixtures cũ theo schema mới và ghi lý do thay test trong `CHANGELOG.md`.
