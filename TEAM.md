# TEAM

**Tên nhóm:** Beluga  **Số người:** 4  (khớp `team_size` trong `game.contract.json`)

| Thành viên | GitHub handle | Module chính | Vai quy trình | Người dự phòng cho |
|---|---|---|---|---|
| Đăng Khắc Hoàng Minh | `dangkhacm-a11y` | `sim/gather` | PO | `tad-4963` |
| Trần Anh Dũng | `tad-4963` | `sim/gather`, `sim/quan`, `client/ui` | Dev / UI | `dangkhacm-a11y` |
| Hà Phan Đại Dương | `DanielHa01` | `sim/quan`, `contracts` | QA lead | `KhiemNTK` |
| Nguyễn Trọng Khiêm | `KhiemNTK` | `sim/day`, `qa` | Integrator / Release | `DanielHa01` |

**Vai quy trình:** PO (đầu mối hỏi giảng viên, giữ `docs/clarify.md`) · Integrator (giữ `docs/contracts/`, gắn tag) · QA lead · Scrum/Release. Có thể kiêm.

## Thỏa thuận làm việc nhóm

- Kênh liên lạc: Nhóm chat chung và trao đổi trực tiếp tại bàn lab.
- Khi bất đồng về thiết kế: Trao đổi tối đa 2 phút dựa trên Test Contract/Ticket; nếu chưa xong, Integrator quyết và ghi vào `docs/clarify.md`.
- Khi ai đó trễ hoặc vướng quá 10 phút: Báo ngay trên kênh nhóm để người dự phòng nhận hỗ trợ hoặc ghép cặp.
- Giờ standup giữa phase: Giữa mỗi phase (phút 20–30 ở Phase 1–2, phút 15–20 ở Phase 3–4), mỗi người báo 1 dòng.
- Cách đọc code của nhau: Mở PR/diff theo lát kề bên trước khi gộp; bắt buộc chạy `unittest` trước khi đẩy lên `main`.
- Cách làm việc với Git: Phase 1–2 làm trên nhánh `feature/*` rồi merge PR vào `main`; Phase 3–4 đồng bộ trực tiếp trên `main` theo quyền sở hữu file; Integrator gắn tag `phase-1`…`phase-4` và `v1.0.0`.
