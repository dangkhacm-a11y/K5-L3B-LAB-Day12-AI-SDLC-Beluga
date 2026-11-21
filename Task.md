# Phân công nhóm — Phase 4 (Test Contract v1.3)

> Thời lượng: 30 phút (2:30–3:00). Mục tiêu: benchmark, ba cảnh báo dễ nhận biết, bàn giao clone sạch, soak nhiều ngày và phát hành `phase-4` + GitHub Release `v1.0.0` từ cùng commit trên `main`. Bắt buộc cho nhóm 4 người; mục leaderboard là mở rộng tự chọn. Chia theo quyền sở hữu file để giảm xung đột.

## Thành viên 1 — Benchmark, soak và báo cáo hiệu năng

- **Phạm vi:** `game.contract.json` (phối hợp với M3), benchmark/soak entry points và test/proof hiệu năng.
- Khai báo `bench_cmd` và `soak_cmd` ở gốc manifest; nâng `contract_version` lên `1.3` nhưng giữ nguyên gameplay/tuning/kho/JSONL v1.2.
- Benchmark nhận `--seed <int> --duration <giây> --out <json>`, xuất đúng `avg_fps`, `p1_low_fps`, `frames`, `measured_s`, `load_ms`; lệnh phải chạy được và tạo artifact. Báo cáo các mục tiêu `avg_fps >= 60`, `p1_low_fps >= 30`, `load_ms <= 10000` mà không biến chúng thành điều kiện cứng.
- Soak nhận `--seed <int> --days <N> --out <json>`; chạy 10 ngày trong một tiến trình headless qua Gather → Quán → Shop, lặp kế hoạch D1–D5 cho D6–D10, giữ tiền/thu nhập/uy tín/nâng cấp/ID cá thể liên tục. `soak.json`: `days`, `days_completed`, `crashes`, `results`, `duration_s`; mỗi kết quả ngày có `day`, `earned`, `reputation`, `score` lúc Shop đóng. Đạt khi `days_completed == days` và `crashes == 0`; không chấm thời gian hoặc bộ nhớ.
- **Bàn giao:** test CLI/schema/tính lặp; `docs/proof/phase-4/bench.json`, `soak.json`, log lệnh và kết quả commit.

## Thành viên 2 — HUD cảnh báo và tương phản cao

- **Phạm vi:** `chonoi/web/`, `chonoi/live.py`/client và test giao diện; không thay đổi luật mô phỏng.
- Dùng chữ hoặc biểu tượng để nhận biết ba cảnh báo: thủy quái đến gần, oxy sắp hết, khách sắp giận. Thêm chế độ tương phản cao; thử cả ba cảnh báo trong chế độ đó. Kiểm tra phụ đề/cảnh báo âm thanh khi tắt âm thanh để xác nhận vẫn xuất hiện đúng lúc.
- Giữ phần sáng tạo tùy chọn tắt trong headless hoặc chứng minh kết quả Test Contract không đổi.
- **Bàn giao:** test/ảnh hoặc video cảnh báo thường và tương phản cao tại `docs/proof/phase-4/`.

## Thành viên 3 — Contract v1.3, docs và bàn giao clone sạch

- **Phạm vi:** `game.contract.json` cùng M1; `README.md`, `CHANGELOG.md`, `CREDITS.md`, `LICENSE`, docs thành viên, verification và hướng dẫn phát hành.
- Rà soát môi trường, điều khiển, test, headless, benchmark và tối đa ba lệnh để clone sạch trên macOS/Linux chạy bản giao diện theo README. Chỉ ghi lệnh đã kiểm chứng.
- Cập nhật CHANGELOG theo phase; rà CREDITS/LICENSE; soạn release notes v1.0.0 gồm điểm mới, cách chạy và giới hạn đã biết.
- Tạo `docs/verification/phase-4.md` với AC-P4-xx → bằng chứng → lệnh/kết quả → commit; cập nhật `docs/clarify.md`, `docs/ai-usage-log.md`. Mỗi người thêm `docs/members/<handle>.md` tối đa 200 từ: phần đã làm, hỗ trợ, lỗi AI được phát hiện/cách xác minh, bài học, liên kết commit/bằng chứng.
- **Bàn giao:** README làm theo được từ clone sạch; checklist đóng gói/release notes khớp commit.

## Thành viên 4 — Điều phối kiểm chứng, release và retro

- **Phạm vi:** tích hợp test M1–M3; `docs/retro.md`; quản lý commit bàn giao, tag và GitHub Release. Không sửa luật/contract/UI thay chủ sở hữu nếu chưa phối hợp.
- Chạy regression P1–P3 còn hiệu lực; smoke ba cảnh báo/tương phản cao; kiểm tra benchmark/soak artifacts từ commit bàn giao. Dùng store riêng nếu thử leaderboard.
- Mở đầu retro bằng việc rà hành động P2: điều đã làm, vướng mắc/lý do, điều tốt, điều cần sửa và hành động tiếp theo; nêu một lỗi AI và cách nhóm xác minh. Đối chiếu tự phản tư thành viên; không dùng số PR/review để chấm cá nhân.
- Chốt `main`, gắn tag `phase-4` và phát hành GitHub Release `v1.0.0` cùng trỏ tới một commit `main`; đính kèm gói chạy được trước 3:00. Không ghi đạt khi thiếu bằng chứng.
- **Bàn giao:** verification, proof, retro, tag và release cùng chỉ đúng commit đã kiểm chứng.

## Mở rộng tự chọn — Leaderboard cục bộ

> Chỉ bắt đầu sau khi AC bắt buộc đạt và nhóm còn thời gian; đây không phải điều kiện bắt buộc của nhóm 4 người.

- Khai báo `leaderboard` trong `extensions`; lưu top 10 bền vững cục bộ, chỉ ghi một mục cho lượt chuẩn đủ 5 ngày; xếp điểm giảm dần, hòa thì lần ghi trước đứng trước kể cả sau khi mở lại.
- `run_cmd --export-leaderboard <out.json> [--leaderboard <store.json>]` xuất `{"entries":[{"name":"...","score":0,"days_completed":5,"seed":0}]}`; tên Unicode không rỗng.
- Headless `day` nhận cặp `--leaderboard <store.json> --player-name <name>`; chỉ ghi đúng một mục khi đủ 5 ngày chuẩn, không scenario, `reason == "days_complete"`. Thiếu một cờ trong cặp hoặc sai mode trả mã 2. Soak không ghi leaderboard; leaderboard không làm đổi JSONL.
- **Bàn giao:** test thứ tự hòa, persistence, validate flags/mode, Unicode và bất biến JSONL; proof dùng store tạm.

## Thứ tự làm việc và tiêu chí nghiệm thu

1. **Phút 0–5:** chốt chủ sở hữu manifest, tên CLI/đường dẫn, cách đo FPS/load, cách tạo input/bot deterministic cho 10 ngày, tên binary/package. Ghi quyết định chưa có trong ticket vào `docs/clarify.md`; không tự đặt semantics.
2. **Phút 5–18:** M1 làm bench/soak; M2 làm cảnh báo; M3 làm contract/README; M4 chuẩn bị ma trận regression, retro và artifact release. Thống nhất commit/API trước khi tích hợp.
3. **Phút 18–25:** ghép; chạy benchmark, soak 10 ngày, ba cảnh báo ở tương phản cao, regression P1–P3; lưu output từ đúng commit ứng viên.
4. **Phút 25–30:** thử clone sạch macOS/Linux tối đa ba lệnh; chốt README/CHANGELOG/credits/license/reflections/verification; kiểm tra gói phát hành.
5. Trước **3:00**, đưa bằng chứng lên `main`, rồi gắn `phase-4` và phát hành `v1.0.0` trên cùng commit.

### AC-P4 bắt buộc

- `contract_version` là `1.3`, có `bench_cmd` và `soak_cmd` ở gốc, vẫn tương thích gameplay/tuning/kho/JSONL v1.2.
- Benchmark tạo JSON đúng năm trường; báo cáo ba mục tiêu hiệu năng; artifact đến từ commit bàn giao.
- Soak chạy 10 ngày trong một tiến trình, đủ ba phase mỗi ngày, lặp kế hoạch đúng, không crash, ID/trạng thái kinh tế liên tục; artifact đúng schema.
- Ba cảnh báo có chữ/biểu tượng; cả ba hiển thị ở tương phản cao; phụ đề/cảnh báo vẫn đúng khi tắt âm thanh.
- Clone sạch macOS/Linux chạy theo README tối đa ba lệnh; README ghi môi trường, điều khiển, test, headless, bench.
- Regression P1–P3 còn hiệu lực đạt; `docs/verification/phase-4.md`, proof, CHANGELOG/release notes và clarify/AI log khớp commit.
- Retro rà hành động P2; phản tư từng thành viên tối đa 200 từ có bằng chứng; LICENSE/CREDITS được rà soát.
- `phase-4` và GitHub Release `v1.0.0` trỏ cùng commit trên `main`, kèm gói chạy được.

### Demo sau 3:00

Demo trực tiếp hoặc video MP4 dưới 5 phút dùng cùng checklist: chạy một Ngày từ Gather qua mở Quán đến đóng Shop; trình bày kết quả test; chỉ ra bằng chứng phân công/phối hợp/đóng góp; mở ma trận truy vết và chỉ bằng chứng tương ứng.
