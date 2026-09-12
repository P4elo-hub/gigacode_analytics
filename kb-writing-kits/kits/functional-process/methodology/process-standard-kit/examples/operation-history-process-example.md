<!--
Imported from: process-standard-kit/examples\operation-history-process-example.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### Процесс — Подключение источника External Source к истории событий

**Контекст процесса:**

| Элемент | Значение |
|---|---|
| Фича | Подключение External Source GetEvents |
| Scope процесса | Получение истории событий с учетом событий внешнего источника External Source |
| Связанные requirements | `01-Requirements/bph-getlink-events-requirements.md` |
| Статус | draft |

**Участники:**

| Участник | Тип | Роль в процессе | Статус подтверждения |
|---|---|---|---|
| Целевой backend-сервис | system | Агрегирует источники | Подтверждено из контекста проекта |
| External Source System | external | Возвращает события внешнего источника | Подтверждено — вы |

**текущее поведение:**

| Шаг | Участник | Действие | Вход | Выход | Решение / правило |
|---|---|---|---|---|---|


| Шаг | Участник | Действие | Вход | Выход | Решение / правило |
|---|---|---|---|---|---|
| 3 | Целевой backend-сервис | Запрашивает внешний источник | Запрос пользовательского сценария | Данные источника в исходной модели | Подтверждено источниками проекта |

**Изменения процесса:**

| Тип изменения | Было | Стало | Причина / requirement |
|---|---|---|---|
| added | История не учитывает External Source | Добавлен запрос к External Source GetEvents | Требование подключить новый источник |
| changed | Список строится по текущим источникам | Список дополняется событиями внешнего источника | Подтверждено — вы |

**Связанные артефакты:**

| Артефакт | Зачем нужен | Path / gap |
|---|---|---|
| Use Case | Сценарий просмотра истории | `02-Use-Cases/bph-history-use-case.md` |
| Sequence Diagram | Взаимодействие целевого сервиса и внешнего источника | `02-UML/integration-sequence.md` |

**Gaps и допущения:**

| ID | Где найдено | Что неизвестно / что предположено / что спроектировано | Как закрыть |
|---|---|---|---|
