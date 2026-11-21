# Ma trận truy vết Phase 4 — TICKET-04 (v1.0.0)

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-4/...`) | Kết quả |
|---|---|---|---|
| AC-P4-UI-01: Ba cảnh báo bằng chữ + biểu tượng (thủy quái đến gần, oxy sắp hết / hết hơi, khách sắp giận) | `tests/test_ui_alerts_p4.py` + kiểm thử trực tiếp trên `chonoi.live` (`gather` & `quan`) | [member-2-ui-alerts.txt](../proof/phase-4/member-2-ui-alerts.txt) | Đạt |
| AC-P4-UI-02: Chế độ tương phản cao (`H` / nút `🌓`) áp dụng cho cả Gather & Quán và cả 3 cảnh báo | `tests/test_ui_alerts_p4.py` (`body.hc`, `btn-hc`) + kiểm thử trực tiếp | [member-2-ui-alerts.txt](../proof/phase-4/member-2-ui-alerts.txt) | Đạt |
| AC-P4-UI-03: Phụ đề SFX & cảnh báo hiển thị đúng lúc khi tắt âm thanh (`M` / nút `🔇`) | `tests/test_ui_alerts_p4.py` (`btn-mute`, `btn-sub`, `subtitle-box`, `SFX_LABELS`) | [member-2-ui-alerts.txt](../proof/phase-4/member-2-ui-alerts.txt) | Đạt |
| AC-P4-BENCH / SOAK / CONTRACT v1.3 / RELEASE v1.0.0 / RETRO | Các lát Thành viên 1, 3, 4 và tích hợp cuối | Chưa có | Chưa kiểm chứng |
