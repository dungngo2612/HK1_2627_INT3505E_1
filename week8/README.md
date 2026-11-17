# Buổi 8 — API Testing và Quality Assurance

| Phần | Thư mục | Báo cáo |
| --- | --- | --- |
| Lab 4 — Load test Books API với Locust | [lab4](lab4/README.md) | [analysis.md](lab4/analysis.md) |
| Bài tập về nhà 2 — Load test endpoint chính, đề xuất SLO | [bai_tap_ve_nha_2](bai_tap_ve_nha_2/README.md) | [analysis.md](bai_tap_ve_nha_2/analysis.md) |

Tất cả mã bài làm, báo cáo Markdown và kết quả đo nằm trong `week8/`.
Bài tập về nhà 2 dùng lại Product API của tuần 7; Lab 4 có Books API riêng
dựa trên starter của giảng viên.

## Cài đặt từ thư mục gốc project

```sh
python3 -m venv week8/.venv
week8/.venv/bin/python -m pip install -r week8/requirements-lock.txt
```

Chạy Lab 4:

```sh
week8/.venv/bin/python week8/lab4/run_load_test.py --bonus
```

Chạy bài tập về nhà 2:

```sh
week8/.venv/bin/python week8/bai_tap_ve_nha_2/run_load_test.py
```

Mỗi phần có `README.md` ghi chi tiết kịch bản, cách chạy và bài nộp.

Bài nộp Lab 4 đã đóng gói: [lab04.zip](lab04.zip).
