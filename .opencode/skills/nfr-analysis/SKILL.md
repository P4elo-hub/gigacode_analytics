---
name: nfr-analysis
description: >-
  Пишет НФТ 5.1 / 5.2 / 5.4 / 5.5. Форма — nfr-standard-kit. Не пишет логи и метрики.
disable-model-invocation: true
---

# nfr-analysis

Маршрут блока `nfr`. Форма подраздела — его template/gate в kit.
Логи и метрики — скилл `observability-analysis`, сюда не включай.

База: `kb-writing-kits/kits/nfr/methodology/nfr-standard-kit/`

Skill kit: `skills/nfr-analysis/SKILL.md`

| Раздел | Template | Example | Gate |
|--------|----------|---------|------|
| 5.1 security | `templates/security.template.md` | — | `quality-gates/security-review.yaml` |
| 5.2 performance | `templates/performance.template.md` | `examples/account-transfer-performance-example.md` | `quality-gates/performance-review.yaml` |
| 5.2 reliability | `templates/reliability.template.md` | `examples/account-transfer-reliability-example.md` | `quality-gates/reliability-review.yaml` |
| 5.4 configuration | `templates/configuration.template.md` | `examples/account-transfer-configuration-example.md` | `quality-gates/configuration-review.yaml` |
| 5.5 toggles | `templates/feature-toggles.template.md` | `examples/account-transfer-feature-toggles-example.md` | `quality-gates/feature-toggles-review.yaml` |

Пиши только `active_sections` задания.

1. Для каждого выбранного раздела прочитай template, example (если есть) и gate целиком.
2. Пиши ровно по kit этого раздела.
3. Нет факта → `[GAP-...]`. Верни только Markdown блока `nfr`.
