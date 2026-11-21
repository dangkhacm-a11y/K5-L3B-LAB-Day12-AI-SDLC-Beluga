# Retro nhóm

## Phase 2 (nhanh)
- **Điều tốt:** Chia rõ 4 lát theo file (`gather.py` cá / quái, `quan.py`, `day.py`), merge PR khá mượt và giữ được bộ test tự động xanh xuyên suốt Phase 1–2 (106/106 test sau khi tích hợp).
- **Điều tệ:** Một số file dùng chung (`game.contract.json`, `chonoi/contract.py`, `chonoi/runner.py`) bị sửa đồng thời gây xung đột nhẹ và làm rơi `Session.tick` khi gộp tay.
- **1 hành động cho Phase 3:** Chốt chủ sở hữu duy nhất cho hợp đồng/adapter kho v1.2 trước khi sửa song song, và bắt buộc chạy `unittest` sau mỗi lần merge vào `main` (chủ trì: Integrator `KhiemNTK` + cả nhóm).

## Phase 4 (cuối)
- **Rà lại hành động Phase 2: đã làm chưa? vì sao?** Đã áp dụng một phần: Phase 3 phân rõ quyền sở hữu `quan.py` (TV2) tách khỏi `gather.py` (TV1) nên không còn xung đột code hai lát này; tuy nhiên nhánh adapter `chonoi/inventory.py` chưa hợp nhất kịp trước khi `gather.py` đổi `hold` sang cá thể nên vẫn có độ lệch tạm giữa `gather.inventory_items()` và `write_inventory()`.
- **Điều tốt / điều tệ:**
  - *Tốt:* Tiến độ nhanh, có test tự động và bằng chứng rõ theo từng phase, hoàn thành thêm mở rộng Lao xua (`weapon`), phụ đề SFX và gắn asset CC0 (Kenney) không ảnh hưởng headless.
  - *Tệ:* Khác biệt lệnh `python3` vs `python` trên Windows và đồng bộ hợp đồng v1.2 giữa các nhánh tốn thêm thời gian rà soát cuối giờ.
- **Số liệu:** 4 thành viên (`dangkhacm-a11y`, `tad-4963`, `DanielHa01`, `KhiemNTK`), mỗi thành viên đều có ≥ 3 commit có nội dung trên repo chung; review chéo lát kề bên qua PR/diff; nhật ký AI ghi đầy đủ theo phase tại `docs/ai-usage-log.md`.
- **Một lần AI sai và cách nhóm phát hiện:** Ở Phase 2, AI áp dụng nâng cấp Shop ngay trong ngày hiện tại thay vì ngày kế tiếp (`KhiemNTK` phát hiện qua spec TICKET-02 và tách `active_upgrades`); ở Phase 1, AI giả định partial fill khi bắt `ca_linh` lúc giỏ thiếu chỗ (`tad-4963` ghi `docs/clarify.md` và đối chiếu TICKET-02 §1.1 sửa lại).
- **Nếu làm lại, đổi gì:** Dành trọn 5 phút đầu mỗi phase để đẩy khung schema/adapter v1.x lên `main` trước tiên, sau đó các thành viên mới tách việc trên cùng một giao diện dữ liệu đã khóa.
