<!--
Imported from: acceptance-test-standard-kit/README.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
# Acceptance Test Standard Kit

Этот каталог описывает приемочные сценарии фичи: Given/When/Then, positive/negative cases, regression scope, test data, environments and traceability to requirements.

## Зачем нужен kit

Acceptance kit нужен, чтобы требования стали проверяемыми перед передачей в разработку и QA.

| Слой | Зачем нужен | Что лежит здесь |
|---|---|---|
| `skills/` | Учит агента писать приемочные сценарии. | `acceptance-test-analysis/SKILL.md` |
| `spec-kit/` | Задает контракт тестового артефакта. | `acceptance-tests.schema.yaml` |
| `templates/` | Дает форму документа. | `acceptance-tests.template.md` |
| `examples/` | Показывает ожидаемый стиль. | `operation-sorting-acceptance-example.md` |
| `quality-gates/` | Проверяет готовность приемочных тестов. | `acceptance-tests-review.yaml` |

## Когда применять

Применяй kit, если нужно:

- сформулировать acceptance criteria как сценарии;
- покрыть positive/negative/edge cases;
- связать тесты с requirements/use cases;
- определить test data;
- обозначить regression scope.
