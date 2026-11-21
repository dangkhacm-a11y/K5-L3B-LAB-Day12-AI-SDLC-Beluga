# Phân công công việc nhóm

> Thay thế bằng kế hoạch Phase 2 theo TICKET-02. Thành viên chưa được ghi tên trong `TEAM.md`, nên tạm đánh số 1–4; điền handle và vai trò trước khi bắt đầu. Phạm vi ưu tiên là lõi Test Contract v1.1; chưa nhận mục mở rộng.

## Thành viên 1 — Gather: số chuẩn, cá bơi và sinh cá

- **Phạm vi:** dữ liệu tuning gather trong `game.contract.json`; `chonoi/sim/gather.py`; validation/schema liên quan trong `chonoi/contract.py` và `chonoi/scenario.py`; test gather.
- Cập nhật contract lên `1.1` theo số chuẩn ticket: thêm N5/N6, `ca_keo` và yield; thiết lập danh sách/miền độ sâu, điểm sinh, trọng số, chu kỳ và trần đàn.
- Làm cá bơi 1.5 m/s, đổi hướng theo seed đúng các bước 120 tick, phản xạ ở mép; 8 đàn đầu ca; sinh tối đa một đàn ở lịch 360 tick, bỏ lượt khi không có điểm hợp lệ, đàn mới hoạt động từ tick sau.
- Giữ tương thích gather độc lập/ngày và fixture `random_fish:false`; dùng `Streams`, `ids.sort_by_id`, `IdAllocator`.
- **Bàn giao:** code, test số chuẩn/cá, và bằng chứng gather. Phối hợp Thành viên 2 về thứ tự di chuyển gather/quái; với Thành viên 4 về phase/tick trong `day`.

## Thành viên 2 — Gather: Cá Sấu, va chạm và ngất

- **Phạm vi:** `chonoi/sim/gather.py` (phần quái), tuning/schema quái, scenario và test.
- Cài dữ liệu loài/quần thể theo ngày; patrol/chase, phát hiện và thoát chase, giới hạn độ sâu/biên; va chạm sau khi cả hai di chuyển, chọn mục tiêu gần nhất rồi theo id.
- Xử lý trừ Máu, bất tử 90 tick, rơi `floor(đang mang/2)` theo LIFO, recoil 60 bước bắt đầu từ bước kế; hit gây ngất phát `faint` với cause/lost/hp và kết thúc gather ngay.
- Giữ luật ngạt: sát thương ngạt xuyên bất tử, không làm rơi nguyên liệu; phối hợp Thành viên 1 để thứ tự tick khớp mục 4.5.
- **Bàn giao:** test patrol/chase/hit/recoil/invulnerability/faint và bằng chứng. Không sửa lặp cùng khối `step` nếu chưa thống nhất với Thành viên 1.

## Thành viên 3 — Quán: số chuẩn, menu và phục vụ

- **Phạm vi:** tuning `quan`/`menu`, `chonoi/sim/quan.py`, validation/schema và test quán.
- Cập nhật hai bếp, bốn bàn, sáu món và công thức/giá/thời gian theo ticket. Cài vòng đời khách, giữ nguyên liệu, chọn món đủ nguyên liệu, nấu/lấy món/phục vụ, ăn, thanh toán, boa và uy tín theo số chuẩn.
- Trong `day`, giới hạn lựa chọn món theo kế hoạch, chọn đều có seed, trừ nguyên liệu đã giữ; trong mode `quan` độc lập vẫn dùng toàn bộ sáu món. Thiếu món khi có bàn thì xử lý `no_dish` theo luật.
- **Bàn giao:** test event và snapshot bếp/bàn/khách, ca kết thúc; xác nhận kho đầu vào khớp đầu ra gather. Trao đổi interface với Thành viên 4 sớm để ghép vòng ngày.

## Thành viên 4 — Vòng ngày, kế hoạch, Shop, pause/UI và tích hợp

- **Phạm vi:** điều phối `day`/Shop/pause, `chonoi/headless.py`, `chonoi/runner.py` hoặc module điều phối mới; UI/HUD và test hộp đen; tài liệu kiểm chứng.
- Cài chu trình DayIntro → gather → EveningIntro → quan → DayResult → Shop; kế hoạch D1–D5 và nguyên liệu tính từ công thức; chuyển kho trong bộ nhớ, kể cả khi ngất; giữ tiền/earned/uy tín/cấp qua ngày.
- Cài Shop, mua upgrade theo dữ liệu, giới hạn cấp/tiền, áp cấp từ ngày kế; `shop_done`, tự đóng sau 600 tick; hoàn tất sau Shop ngày 5. Cài pause để dừng timer/gameplay và resume đúng cạnh.
- Cập nhật CLI `--mode day --days`, output snapshot/event/end theo v1.1; làm menu/HUD cần cho luồng chơi và hỗ trợ smoke/regression toàn nhóm.
- **Bàn giao:** smoke gather→quan và `day --days 1`/nhiều ngày, bằng chứng ở `docs/proof/phase-2/`, ma trận `docs/verification/phase-2.md`, kiểm tra tài liệu/nhánh/tag cùng Integrator.

## Phụ thuộc và cách ghép

1. Kickoff 5 phút: chốt một người Integrator (khuyến nghị Thành viên 4), người PO giữ `docs/clarify.md`; thống nhất `contract_version: 1.1`, schema và event giữa gather, quan, day/shop. Mọi người cùng rà soát thay đổi contract/tuning vì ảnh hưởng nhiều lát.
2. Thành viên 1 và 2 cùng chốt thứ tự một tick gather theo mục 4.5 trước khi sửa `step`; Thành viên 3 gửi interface kho/menu cho Thành viên 4 trước khi luồng day bắt đầu.
3. Làm trước các fixture cố định để day tích hợp sớm; ghép theo commit nhỏ, review chéo lát kề bên. Không sửa test để che lỗi luật; test thay đổi theo số chuẩn phải ghi lý do.
4. Không nhận phần mở rộng (weapon/net/snake/burn/vendor/ca_ho/settings) cho tới khi lõi chạy và có bằng chứng. Dữ liệu gameplay lấy từ contract; RNG đi qua `Streams`, entity sort bằng `ids.sort_by_id`, ID cấp bằng `IdAllocator`.

## Mốc bàn giao Phase 2

- **Phút 0–5:** chốt contract/interface, điền `TEAM.md`, cập nhật danh sách AC trong `docs/verification/phase-2.md`.
- **Phút 5–20:** hoàn thành lõi các lát và cập nhật test cùng cấu hình/spec.
- **Phút 20:** smoke gather→quan, lưu output ở `docs/proof/phase-2/`; standup và điều người đã xong sang lát trễ.
- **Phút 20–45:** ghép `day`, Shop, pause/UI; chạy smoke một ngày, nhiều ngày và regression Phase 1 với số chuẩn.
- **Phút 45–55:** cập nhật `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/retro.md`; chốt verification/bằng chứng, gắn tag `phase-2` lên commit bàn giao trên `main` trước phút 55.

## Kiểm chứng bắt buộc

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --out gather.jsonl
python3 -m chonoi.headless --mode quan --seed 1 --ticks 600 --out quan.jsonl
python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day.jsonl
```

Bổ sung chạy nhiều ngày (`--days 5`) và smoke chuyển kho theo ticket. Ghi lệnh, commit, kết quả và đường dẫn bằng chứng vào `docs/verification/phase-2.md`; không ghi “đạt” nếu chưa chạy được.
