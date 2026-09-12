# challenge-feature — reference

## ID и статусы

| Поле | Формат |
|------|--------|
| Id вопроса | `CH-01`, `CH-02`, … (per slug) |
| Статус в `-challenges.md` | `open` · `covered` · `resolved` · `deferred` |
| Тип | см. таблицу типов ниже |
| Severity | `Critical` · `Major` · `Minor` |

---

## Категории критического разбора

### A. Бизнес-логика и use case

- [ ] Все alt-сценарии TO BE имеют исход (успех / деградация / skip)?
- [ ] Что при конфликте двух BR в runtime?
- [ ] Границы scope: что **явно** out of scope и что случится, если придёт out-of-scope data?
- [ ] Приоритеты источников при partial data (merge, enrichment)?
- [ ] Поведение при «поле есть, но невалидно» vs «поля нет»?

### B. Контракты и интеграции

- [ ] Optional vs required: backward compatibility при rollout?
- [ ] Все enum-ветки описаны?
- [ ] Timeout / error / empty response — что видит пользователь?
- [ ] Версионность proto/OpenAPI upstream?
- [ ] Симметрия sibling-интеграций (одинаковое поле, разный уровень)?

### C. Данные и маппинг

- [ ] Тип, округление, валюта, null, zero?
- [ ] Транзит vs persist: что при рестарте / Ignite / cache miss?
- [ ] Маппинг при rename / deprecated field?

### D. NFR, toggles, конфигурация

- [ ] Prod-default vs test; что если конфиг изменят mid-flight?
- [ ] Feature OFF — деградация или silent skip?
- [ ] Лимиты (maxRecords, deadline) и поведение на границе?

### E. Ошибки и observability

- [ ] Какие ошибки логируются vs отдаются клиенту?
- [ ] Метрики/алерты при systematic missing field?
- [ ] Partial failure в batch (N заявок, одна с ошибкой)?

### F. Безопасность и compliance

- [ ] PII в новом поле; маскирование на UI?
- [ ] Авторизация: кто может видеть доходность?

### G. Тесты и приёмка

- [ ] Есть ли acceptance criteria под каждый Critical/Major CH?
- [ ] Фикстуры под edge (empty yield, BPH-only yield, оба источника)?

---

## Типы вопросов (колонка «Тип»)

| Тип | Когда использовать |
|-----|-------------------|
| `corner-case` | Редкий, но возможный runtime-сценарий |
| `contradiction` | Два утверждения spec/context противоречат |
| `missing-flow` | Alt/error path не описан |
| `scope-ambiguity` | Неясно in/out of scope |
| `contract-edge` | Граница контракта (null, optional, enum) |
| `nfr-hole` | NFR, prod, toggle, perf |
| `data-edge` | Маппинг, тип, persist vs transit |
| `test-gap` | Нет критерия проверки |
| `integration-edge` | Поведение при сбое внешней системы |

---

## Severity

| Severity | Критерий |
|----------|----------|
| **Critical** | Без ответа нельзя безопасно реализовать или возможен silent wrong data |
| **Major** | Высокий риск инцидента / rework; нужен до dev |
| **Minor** | Уточнение формулировки, docs, non-blocking |

---

## Выходной файл: `-challenges.md`

```markdown
---
report_type: feature-challenges
slug: <slug>
source_document: Feature-writing/<slug>/<slug>.md
generated_at: <YYYY-MM-DD>
challenge_iteration: <1|2|…>
language: ru
---

# Критический разбор: <slug>

**Спецификация:** `Feature-writing/<slug>/<slug>.md`
**Банк вопросов:** `Feature-writing/<slug>/<slug>-challenges.md`

## Сводка
- Вопросов: N (Critical: N · Major: N · Minor: N)
- Фокус прогона: [— или тема]

## Бизнес-логика и use case

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-01 | §1.3 alt 4a | Если в ОГ yield пустой, а в BPH — заполнен: обогащение или нет при concurrent update? | corner-case | Major | open |

## Контракты и интеграции

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
```

Пустые категории без вопросов — **не включать**.

---

## Повторный прогон

1. Прочитай существующий `CHALLENGES`.
2. `resolved` / `covered` — не дублировать.
3. Новые находки — новые `CH-NN` (max существующий + 1).
4. Обновить `challenge_iteration`.

Когда запускать повторно:

| Триггер | Причина |
|---------|---------|
| `SPEC` изменён после `CHALLENGES` (mtime) | появились новые § и поведение |
| Закрыты крупные gaps через `/resolve-gaps` | решения открыли новые corner cases |
| `ALIGNMENT` выявил MISMATCH в контрактах | область риска сместилась |

Проверить свежесть: `/feature-status <slug>`.

---

## Связь с другими скиллами

| Скилл | Отличие |
|-------|---------|
| `/check-feature` | Сверка с analytics/code; **правит** spec |
| `/check-feature-code` | Сверка spec с `repositories/` |
| `/resolve-gaps` | Закрывает `[GAP-...]` из spec |
| `/challenge-feature` | Adversarial вопросы → файл; spec не трогает |
| `/resolve-challenges` | Закрывает `CH-*` → правит spec |
| `/feature-status` | Read-only дашборд: что открыто и что дальше |
