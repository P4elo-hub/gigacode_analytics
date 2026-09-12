---
name: check-feature-code
description: >-
  Verifies a feature document in Feature-writing against actual code in
  repositories (DB migrations, contracts, integrations, configs, toggles).
  Writes full report in Russian to Feature-writing/<slug>/<slug>-code-alignment.md;
  brief summary in chat only. Invoke explicitly after /check-feature as final verification gate.
disable-model-invocation: true
---

# check-feature-code

Проверка **соответствия документа фичи коду**. Только чтение и отчёт — документ
**не править** (для правок — `/check-feature`).

Пути и токены: правило `artifact-paths`.

## Когда вызывать

```
/find-context → /write-feature → /check-feature → /resolve-gaps
  → /challenge-feature → /resolve-challenges → /check-feature-code
```

Также запускай повторно, когда `SPEC` изменён после предыдущего отчёта —
`/feature-status <slug>` покажет, что `ALIGNMENT` устарел.

| Критерий | Значение |
|----------|----------|
| Вход | `SPEC` = `Feature-writing/<slug>/<slug>.md` |
| **Выход** | `ALIGNMENT` = `Feature-writing/<slug>/<slug>-code-alignment.md` |
| Источник истины | `repositories/` (код, контракты, миграции, конфиги) |
| Вспомогательно | `CONTEXT_DOC`, `db-export/` |

Текст после `/check-feature-code`:

1. **Идентификатор фичи** (`<slug>`, путь `Feature-writing/<slug>/<slug>.md` или бриф) — **обязателен**.
2. **Приоритетные указания** (опционально) — области для углублённой проверки.

Нет идентификатора → попроси указать фичу и остановись.

## Принципы

1. **Код — источник истины.** Документ описывает намерение; код показывает факт.
2. **Только доказательства.** Каждое замечание — с путём к файлу и фрагментом (строка/якорь).
3. **Не выдумывать.** Не нашёл в коде — `NOT FOUND` или `UNVERIFIABLE`, не додумывай.
4. **Универсальность.** Не опирайся на знание конкретных таблиц/сервисов проекта — извлекай
   сущности из проверяемого документа и ищи их в коде.
5. **Read-only для фичи.** Не редактируй `Feature-writing/<slug>/<slug>.md` или
   `repositories/`. **Разрешена только запись** отчёта в `Feature-writing/<slug>/<slug>-code-alignment.md`.

---

## Цикл после code-alignment

| Параметр | Значение |
|----------|----------|
| `ALIGNMENT_MAX_ITERATIONS` | **3** прогона `/check-feature-code` |
| При FAIL | `/resolve-code-alignment` или targeted `/check-feature` → повтор alignment |
| Выход | `verdict: PASS` / `PASS WITH GAPS` без Critical/Major MISMATCH |
| Лимит исчерпан | Ручной разбор `ALIGNMENT`, 4-й прогон не запускать |

**Правки по отчёту не требуют `/check-feature`:** можно указать `ALIGNMENT` в Agent
и попросить поправить `SPEC` — targeted fix без отдельной slash-команды.

При каждом прогоне увеличивай `alignment_iteration` в frontmatter отчёта (начиная с 1).

---

## Шаг 1. Подготовка

1. Определи `<slug>`. Прочитай **целиком**:
   - `Feature-writing/<slug>/<slug>.md` — **единственный проверяемый документ**;
   - `Feature-context/<slug>.md` — если есть (якоря на код).
2. Если документа фичи нет — сообщи и остановись.
3. Составь **реестр утверждений** из документа — всё, что можно сверить с кодом:

| Категория | Что извлекать из документа |
|-----------|----------------------------|
| Контракты | endpoint, method, path, proto/OpenAPI, поля, типы, required, enum, примеры |
| БД | таблицы, колонки, типы, PK/FK, INSERT/UPDATE/DELETE, changeset/migration id |
| Интеграции | вызываемые сервисы, клиенты, топики, форматы сообщений |
| Конфиги | ключи, значения по умолчанию, env, профили, ConfigMap/Helm |
| Тогглы | имя флага, условие включения, default |
| Поведение | классы/методы, ветвления, коды ошибок, метрики, log-сообщения |

4. Для каждого утверждения зафиксируй: раздел документа, цитата/таблица, ожидаемое поведение.

---

## Шаг 2. Поиск в коде

Для каждого утверждения найди подтверждение в `repositories/`:

```
1. Якорь из Feature-context/<slug>.md
2. Grep по имени таблицы / поля / endpoint / config key / toggle / class / method
3. scripts/find_context.py "<уточнённый запрос>" --terms "..." (если есть в workspace)
4. Навигация: migrations (Liquibase/Flyway/SQL), entity/JPA, mappers, clients, *.yml/*.yaml, *.proto, OpenAPI
```

**DDL/схема:** при расхождении имён колонок сверяй с `db-export/` как справочником,
но **миграции и entity в коде** имеют приоритет над экспортом.

---

## Шаг 3. Сверка по категориям

Подробные чеклисты — [reference.md](reference.md). Кратко:

### 3.1 Контракты

- Имя, тип, формат, обязательность, enum каждого поля — как в OpenAPI/proto/генерируемых классах.
- Примеры request/response валидны против схемы.
- Описанные коды ошибок / HTTP status есть в коде или контракте.

### 3.2 БД и миграции

- Таблица и колонки существуют (migration, entity, `@Table`/`@Column`).
- INSERT: все колонки, значения, типы; literal vs sequence/default.
- UPDATE/DELETE: WHERE, затронутые строки, idempotency.
- Changeset: id, author, preconditions, rollback — если заявлены в документе.
- FK, unique, not null, default — совпадают с DDL/аннотациями.

### 3.3 Интеграции

- URL/path, HTTP method, gRPC service/method — как в клиенте или конфиге.
- Заголовки, query params, body mapping — как в builder/converter.
- Async: topic/queue, key, schema, consumer group — как в коде.

### 3.4 Конфигурация

- Ключ `@ConfigurationProperties` / `@Value` / env — существует.
- Default в документе = default в коде или `application*.yml`.
- Профили (`dev`, `prod`) — если документ их различает.

### 3.5 Feature toggles

- Имя toggle/flag найдено в коде (enum, LaunchDarkly, custom registry).
- Условие «если включён / выключен» соответствует `if`/strategy в коде.
- Default state совпадает.

### 3.6 Алгоритм и поведение

- Упомянутые классы/методы существуют; сигнатуры не противоречат описанию.
- Ветвления (ЕСЛИ/ИНАЧЕ в документе) — порядок проверок и early return как в коде.
- Метрики, WARN/ERROR логи — строки или константы найдены.

---

## Шаг 4. Классификация находок

| Статус | Значение |
|--------|----------|
| **CONFIRMED** | Документ совпадает с кодом |
| **MISMATCH** | Документ противоречит коду (критично) |
| **PARTIAL** | Частично верно (неполный INSERT, устаревшее имя поля) |
| **NOT FOUND** | В коде нет заявленной сущности (новая фича или ошибка документа) |
| **UNVERIFIABLE** | Нельзя подтвердить без runtime/стенда/секретов |

Severity: **Critical** (MISMATCH в контракте/БД/интеграции) · **Major** (PARTIAL, NOT FOUND для TO BE) · **Minor** (формулировка, необязательные поля) · **Info** (CONFIRMED).

---

## Шаг 5. Приоритетные указания пользователя

Если пользователь указал фокус — проверь **в первую очередь** и глубже, затем общий проход.
Указания не отменяют полный реестр; не заменяют код как источник истины.

---

## Шаг 6. Запись отчёта в файл

**Полный отчёт — только в файл.** В диалог пользователю — краткая сводка (см. Шаг 7).

### 6.1 Путь выходного файла

```
Feature-writing/<slug>/<slug>-code-alignment.md
```

- `<slug>` — тот же, что у проверяемого документа `Feature-writing/<slug>/<slug>.md`.
- Если файл уже существует — **перезаписать** (новый прогон аудита).
- Не создавать другие артефакты в `Feature-writing/`.

### 6.2 Содержимое файла

**Язык отчёта — русский.** Заголовки разделов, подписи полей, формулировки находок,
рекомендуемые действия и пояснения пиши по-русски. На английском оставляй только:
технические статусы (`CONFIRMED`, `MISMATCH`, `PASS` и т.д.), идентификаторы в коде,
пути к файлам, имена классов/полей и цитаты из исходников.

Запиши отчёт **целиком** в файл по шаблону ниже. Все таблицы находок, доказательства и
рекомендуемые действия — **только в файл**, не дублируй их полностью в чат.

```markdown
---
report_type: code-alignment
slug: <slug>
source_document: Feature-writing/<slug>/<slug>.md
generated_at: <YYYY-MM-DD>
alignment_iteration: <1|2|3>
scope: repositories/ only
language: ru
verdict: PASS | PASS WITH GAPS | FAIL
---

# Отчёт о соответствии коду: <slug>

**Документ:** `Feature-writing/<slug>/<slug>.md`
**Отчёт:** `Feature-writing/<slug>/<slug>-code-alignment.md`
**Область проверки:** только код в `repositories/`

## Сводка
- CONFIRMED: N · MISMATCH: N · PARTIAL: N · NOT FOUND: N · UNVERIFIABLE: N
- **Вердикт:** PASS | PASS WITH GAPS | FAIL

## Приоритетные находки
[если были указания пользователя; иначе «—»]

## Находки по категориям

### Контракты
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |

### БД и миграции
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |

### Интеграции
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |

### Конфигурация
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |

### Feature toggles
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |

### Поведение и алгоритмы
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |

### Тесты и фикстуры
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
[раздел включай, если в документе фичи есть § про тесты/фикстуры]

## Рекомендуемые действия
1. [Конкретное действие → раздел документа → что исправить; правки через /check-feature или /resolve-code-alignment]

## Пропущено
[что сознательно не проверялось и почему; иначе «—»]
```

**Вердикт:**
- **PASS** — нет Critical/Major MISMATCH.
- **PASS WITH GAPS** — есть NOT FOUND / UNVERIFIABLE для TO BE (ожидаемо до реализации) или Minor.
- **FAIL** — есть Critical/Major MISMATCH.

---

## Шаг 7. Ответ в диалог (кратко)

После записи файла ответь **коротко** — без полных таблиц findings:

```markdown
Соответствие коду: **<verdict>**

Отчёт: `Feature-writing/<slug>/<slug>-code-alignment.md`

- CONFIRMED: N · MISMATCH: N · PARTIAL: N · NOT FOUND: N · UNVERIFIABLE: N
- Critical/Major: [1–3 пункта или «нет»]
- Итерация: N / 3
- Дальше: [одна рекомендация по матрице ниже]
```

Матрица next step:

| Verdict / состояние | Дальше |
|---------------------|--------|
| FAIL, Critical/Major MISMATCH, итераций < 3 | `/resolve-code-alignment <slug>` → повторный прогон |
| PASS WITH GAPS, есть closable вопросы | `/resolve-code-alignment <slug>` (опционально) |
| PASS / PASS WITH GAPS, блокеров нет | **spec готов**; проверить чеклист `/feature-status <slug>` |
| Итераций 3 и всё ещё FAIL | лимит исчерпан: ручной разбор отчёта, не запускать 4-й прогон |

Если запись файла не удалась — сообщи об ошибке и выведи отчёт в чат как fallback.

---

## Антипatterns

- ❌ Править документ фичи (`Feature-writing/<slug>/<slug>.md`) или код в рамках этого скилла.
- ❌ Выводить полный отчёт в диалог — только в `Feature-writing/<slug>/<slug>-code-alignment.md`.
- ❌ Считать Confluence/analytics источником истины вместо кода.
- ❌ Пропускать миграции при проверке INSERT/UPDATE.
- ❌ Подтверждать без пути к файлу в `repositories/`.

## Дополнительно

- Детальные чеклисты: [reference.md](reference.md)
- Правки документа после отчёта: `/check-feature <slug>`
