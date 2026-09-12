# Calibration

Meta-pipeline после PASS: baseline → human review → gold → delta → proposals → benchmark.

```
Calibration/<slug>/
  manifest.json
  runs/run-001/
    inputs.lock.json
    baseline/          ← snapshot до ваших правок
    gold/              ← эталон после review
    review/
      human-review.md
      delta-analysis.md
      context-gaps.md      ← CTX-GAP-* (не хватило analytics/repo/контекста)
      context-gaps.json
    proposals/
      proposals.md
    rerun/             ← изолированный benchmark
    scorecard.json
```

Команды: `/snapshot-baseline`, `/capture-review`, `/analyze-delta`, `/propose-calibration`,
`/apply-calibration`, `/benchmark-rerun`, `/calibrate` (цепочка).

Entry docs: [HOW-WORK-CALIBRATION.md](../HOW-WORK-CALIBRATION.md) (гид),
[CALIBRATION.md](../CALIBRATION.md) (шпаргалка агентов). Папка в `.gitignore`.
