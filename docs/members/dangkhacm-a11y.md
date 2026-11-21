# dangkhacm-a11y — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm (kèm commit/bằng chứng):**
  - Phase 1: luật Gather oxy/ngạt, faint và mất giỏ theo LIFO; [commit d98a9f0](https://github.com/dangkhacm-a11y/K5-L3B-LAB-Day12-AI-SDLC-Beluga/commit/d98a9f0), [commit c4ac2df](https://github.com/dangkhacm-a11y/K5-L3B-LAB-Day12-AI-SDLC-Beluga/commit/c4ac2df).
  - Phase 2: bơi và sinh đàn cá; [commit 435943b](https://github.com/dangkhacm-a11y/K5-L3B-LAB-Day12-AI-SDLC-Beluga/commit/435943b).
  - Phase 3: độ tươi, ID cá thể, mất hàng LIFO và dòng lũ; [commit a97a24a](https://github.com/dangkhacm-a11y/K5-L3B-LAB-Day12-AI-SDLC-Beluga/commit/a97a24a), [bằng chứng kiểm thử](../proof/member-1-phase3-gather.md).
  - Phase 4: lệnh benchmark/soak 10 ngày; [commit 17975bb](https://github.com/dangkhacm-a11y/K5-L3B-LAB-Day12-AI-SDLC-Beluga/commit/17975bb), [proof và giới hạn đã biết](../proof/phase-4/member-1.md).
- **Tôi đã review:** kiểm tra kết quả chạy test và output benchmark/soak trước khi ghi proof.
- **AI sai ở đâu và tôi phát hiện thế nào:** benchmark ban đầu giữ thời gian từng tick trong bộ nhớ; tôi phát hiện qua lượng dữ liệu tăng lớn khi chạy 30 giây và đổi sang bộ đếm/cửa sổ 1 giây. Benchmark hiện đo tick/s, không phải FPS render; giới hạn này được ghi trong clarify/proof.
- **Điều tôi học được:** kiểm tra output và giới hạn phép đo quan trọng không kém việc lệnh chạy thành công.
