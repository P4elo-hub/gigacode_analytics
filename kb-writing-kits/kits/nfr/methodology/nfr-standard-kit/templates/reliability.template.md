<!--
Imported from: nfr-standard-kit/templates\reliability.template.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### NFR — [Название фичи] (Надёжность)

### 7.2. НАДЁЖНОСТЬ

SLA/SLO:
| Метрика | SLO | Описание |
|---------|-----|----------|
| Availability | [значение] | [допустимый простой / контекст] |
| Error rate | [значение] | [для каких событий] |
| Latency p85 | [значение] | [какой endpoint / транзакция] |

Graceful Degradation:
| Зависимость | Поведение при отказе | Fallback |
|-------------|---------------------|----------|
| [сервис / БД / кэш / очередь] | [что делает система] | [отложенная обработка / retry / обходной путь] |
