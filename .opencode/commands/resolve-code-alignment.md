---
description: Закрыть closable gaps из отчёта code-alignment через опрос
agent: alignment-resolver
---

Закрой documentable gaps по скиллу `resolve-code-alignment`: отбери из отчёта
findings, решаемые ответом пользователя (MISMATCH, PARTIAL, UNVERIFIABLE, пункты
Recommended actions про уточнение документа), опроси одним батчем и точечно
поправь спецификацию.

NOT FOUND для TO BE не спрашивай — это ожидаемо до реализации. `verdict` во
frontmatter отчёта не меняй. После правок обязателен повторный
`/check-feature-code` — он закрывает петлю.

Фича (slug) или путь к отчёту code-alignment: $ARGUMENTS
