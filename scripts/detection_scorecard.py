#!/usr/bin/env python3
"""Detection scorecard vs expected occupied-slot counts on batch_new."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_optimizer.vision.binder_grid import detect_binder_slots

BATCH = ROOT / "tests/fixtures/scan/real/batch_new"

# Expected occupied pockets (visual inventory / overlay audit).
# Update when new labeled GT arrives.
EXPECTED: dict[str, int] = {
    "01_IMG_6181-9283dbc4-e689-448b-a464-a09ce79b59a9.png": 4,
    "02_IMG_6182-b851c886-39af-4e6f-a97b-cbb0c4947b4e.png": 7,
    "03_IMG_6183-e6de9672-7af7-4784-980f-6c4138f19ddb.png": 8,
    "04_IMG_6184-e08f1971-4128-495b-96b0-0f6342285a51.png": 8,
    "05_IMG_6185-2737bbe3-3dea-4847-9ccc-01dcbd6baa10.png": 8,
    "06_IMG_6186-0ba58fba-c7e2-4967-bd41-69c4b6c59dc4.png": 7,
    "07_IMG_6187-cdda7eb9-4da2-402e-b1a7-10938c1460f3.png": 9,
    "08_IMG_6188-cbdb97f9-1f19-4d81-b280-55d59390eedb.png": 8,
    "09_IMG_6189-1864ee91-25bd-4824-abf5-fffa505a5fa7.png": 8,
    "10_IMG_6190-21827863-22f2-452b-8b6a-f685ff37350e.png": 8,
    "11_IMG_6191-ff86ab3f-bd67-4188-8215-96dc6178f9c1.png": 8,
    "12_IMG_6192-d32f1f4d-7253-4b8a-b176-b33dc70b57d9.png": 8,
    "13_IMG_6193-38ea6484-48b7-425d-b01a-7cf282c80218.png": 7,
    "14_IMG_6194-7c723314-c4d4-4ef8-a193-46592baba740.png": 9,
    "15_IMG_6195-33c42953-e002-4500-8c11-6bb49b35fff8.png": 8,
    "16_IMG_6196-9a65f2bf-edfa-49f3-bf0a-528a9a2ec49a.png": 8,
    "17_IMG_6197-65f5c3a4-dd32-451f-a384-4ccfe3f221d3.png": 8,
    "18_IMG_6198-5ba79bca-45b1-4687-981e-428d37d4d6f7.png": 7,
    "19_IMG_6199-7c7b5fcb-a151-435e-8e51-8679738b0502.png": 7,
    "20_IMG_6200-97cd2180-ab71-42e5-b7b5-a2ef46922d44.png": 9,
    "21_IMG_6201-1750c780-235d-4dc0-a7e6-075920794b93.png": 9,
    "22_IMG_6202-a1770e44-0189-4daf-a3aa-604fd5d07b43.png": 8,
    "23_IMG_6203-374f2f39-9c6f-43af-80c8-ebda5171a44b.png": 9,
    "24_IMG_6204-88633bc6-6a4c-49fe-8c84-479705f6931e.png": 5,
    "25_IMG_6205-ab56973a-5db8-4b26-8996-5988faefcc4d.png": 6,
    "26_IMG_6206-b2d96958-3956-4933-835f-e81ef1042d5f.png": 8,
    "27_IMG_6207-8b165030-3e7c-445b-86dc-d7035e1d3305.png": 9,
    "28_IMG_6208-f035ade7-1840-4fed-808c-0881696e83cb.png": 9,
    "29_IMG_6209-234acd48-8658-4dc0-bd6a-944298e578a3.png": 9,
    "30_IMG_6210-e5661c8c-75d3-44f7-8e54-53d174d015fc.png": 9,
    "31_IMG_6211-ce0a5906-12e4-4dba-a98e-081b8786fb9b.png": 8,
    "32_IMG_6212-71b631fc-6504-4a4a-8d9a-1c9cc152d36f.png": 9,
    "33_IMG_6213-b86acb01-446a-49bf-90b7-00c9d619c9f9.png": 9,
    "34_IMG_6214-c3c575e2-f7ab-4e34-8965-75f865ec67a8.png": 9,
    "35_IMG_6215-9e0108e8-e960-41ca-aa6d-a5667630b68b.png": 9,
    "36_IMG_6216-56d8d611-6cb7-446e-a581-23fe53fe83e4.png": 9,
    "37_IMG_6217-ee1fbfb6-48e8-48ff-8b45-0f11b72c9227.png": 9,
    "38_IMG_6218-e1cacfd6-66a9-4ea9-a9f5-29b5e0813464.png": 9,
    "39_IMG_6219-1f79c5e6-f833-477a-a5c1-4ef042311f8a.png": 8,
    "40_IMG_6220-842c5ac9-507a-4709-be54-1941df198536.png": 9,
}


def main() -> None:
    rows = []
    tp = fp = fn = 0
    exact = 0
    for name, exp in sorted(EXPECTED.items()):
        path = BATCH / name
        n = len(detect_binder_slots(str(path)))
        # count-based: matched = min(n,exp), fp = max(0,n-exp), fn = max(0,exp-n)
        matched = min(n, exp)
        fp_i = max(0, n - exp)
        fn_i = max(0, exp - n)
        tp += matched
        fp += fp_i
        fn += fn_i
        if n == exp:
            exact += 1
        rows.append({"file": name, "n": n, "exp": exp, "fp": fp_i, "fn": fn_i})
        if fp_i or fn_i:
            print(f"DIFF n={n} exp={exp} fp={fp_i} fn={fn_i}  {name[:48]}")

    prec = tp / (tp + fp) if (tp + fp) else 0
    rec = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
    print(
        f"\nimages={len(EXPECTED)} exact={exact}/{len(EXPECTED)} "
        f"({100*exact/len(EXPECTED):.1f}%)"
    )
    print(
        f"slot-count precision={100*prec:.1f}%  recall={100*rec:.1f}%  "
        f"F1={100*f1:.1f}%  (tp={tp} fp={fp} fn={fn})"
    )
    out = BATCH.parent / "overlays_batch_new" / "detection_scorecard.json"
    out.write_text(
        json.dumps(
            {
                "exact_pct": round(100 * exact / len(EXPECTED), 2),
                "precision_pct": round(100 * prec, 2),
                "recall_pct": round(100 * rec, 2),
                "f1_pct": round(100 * f1, 2),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "rows": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
