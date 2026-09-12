# check-feature-code — reference checklists

Универсальные чеклисты. Конкретные имена таблиц, сервисов и полей **берутся только
из проверяемого документа** `Feature-writing/<slug>/<slug>.md`, не из этого файла.

---

## A. Контракты (REST / gRPC / GraphQL / SOAP / Async schema)

### A.1 Идентификация контракта в коде

| Протокол | Где искать в `repositories/` |
|----------|------------------------------|
| REST | `*openapi*`, `*swagger*`, `@RequestMapping`, `@GetMapping`, controller classes |
| gRPC | `*.proto`, generated stubs, `@GrpcService` |
| GraphQL | schema files, resolver classes |
| SOAP | WSDL, JAX-WS annotations |
| Async | Avro/JSON schema, `@KafkaListener`, topic constants |

### A.2 Поле за полем

- [ ] Имя поля (JSON/proto tag) совпадает
- [ ] Тип (string, int32, big_decimal, date-time, uuid, …) совпадает
- [ ] Формат / pattern / min / max / length совпадают
- [ ] required vs optional vs nullable совпадает
- [ ] enum: все значения документа ∈ enum в контракте; нет лишних в контракте, если документ заявляет полноту
- [ ] Вложенность и имена wrapper-объектов (data/items/error) совпадают

### A.3 Примеры

- [ ] Каждый пример парсится против схемы
- [ ] Обязательные поля присутствуют
- [ ] Типы значений корректны (число vs строка, формат даты)
- [ ] enum-значения из допустимого набора

### A.4 Ошибки и статусы

- [ ] HTTP/gRPC status codes из документа описаны в контракте или exception handler
- [ ] Тела ошибок (code, message) совпадают с DTO/константами

---

## B. База данных и миграции

### B.1 Где искать

| Артефакт | Типичные пути |
|----------|---------------|
| DDL / DML | `db/changelog`, `liquibase`, `flyway`, `V*__*.sql`, `*.sql` |
| ORM | `@Entity`, `@Table`, `@Column`, JPA repositories |
| Raw SQL | `*Repository*.java`, `*Mapper.xml`, `@Query` |

### B.2 Таблицы и колонки

- [ ] Имя таблицы (schema.table) существует
- [ ] Каждая колонка из документа есть в DDL/entity
- [ ] Тип данных (varchar(n), numeric, timestamp, boolean, jsonb, …) совпадает
- [ ] NULL / NOT NULL совпадает
- [ ] DEFAULT совпадает
- [ ] PK, UK, FK, index — если документ их упоминает

### B.3 INSERT

- [ ] Перечислены все обязательные колонки (NOT NULL без default)
- [ ] Значения литералов совпадают с миграцией (строки, числа, boolean)
- [ ] Ссылки на FK (id других таблиц) — логика получения id описана верно
- [ ] Sequence / auto-increment — не подставлен фиктивный id, если в коде generated
- [ ] Несколько INSERT — порядок и зависимости FK корректны

### B.4 UPDATE

- [ ] SET-колонки существуют
- [ ] WHERE однозначно идентифицирует строки (не «обновить все» без оговорки)
- [ ] Условие WHERE соответствует бизнес-правилу в коде

### B.5 DELETE

- [ ] Soft delete (deleted flag) vs hard delete — как в коде
- [ ] CASCADE / ограничения FK учтены

### B.6 Liquibase / Flyway

- [ ] changeset id / author — если документ их цитирует
- [ ] preConditions — если заявлены
- [ ] rollback — если заявлен
- [ ] Idempotency (ON CONFLICT, MERGE, WHERE NOT EXISTS) — если заявлена

### B.7 AS IS vs TO BE

- **AS IS:** утверждение «сейчас в БД …» — подтверди текущими миграциями/данными seed.
- **TO BE:** «будет добавлено …» — NOT FOUND допустим до merge; пометь severity Major, не Mismatch.

---

## C. Интеграции

### C.1 Синхронные вызовы

- [ ] Base URL / service name — config или service discovery
- [ ] Path + HTTP method / gRPC full method name
- [ ] Request headers (auth, correlation-id, content-type)
- [ ] Query parameters и body — mapping в client DTO
- [ ] Timeout, retry — если описаны в документе

### C.2 Асинхронные

- [ ] Topic / queue / exchange name — константа или config key
- [ ] Message key, partition strategy
- [ ] Schema (Avro/JSON) — поля сообщения
- [ ] Consumer group / subscription name
- [ ] DLQ / retry topic — если описано

### C.3 Маппинг request/response

- [ ] Поля документа ↔ поля DTO/converter
- [ ] Преобразования (enum mapping, date format, null → "") — сверить с converter/mapper

---

## D. Конфигурация

### D.1 Где искать

- `application.yml`, `application-*.yml`, `bootstrap.yml`
- `@ConfigurationProperties` classes
- `@Value("${...}")`
- Helm `values.yaml`, ConfigMap templates
- Environment variable names in deployment manifests

### D.2 Чеклист

- [ ] Ключ конфигурации существует
- [ ] Default value в документе = default в yml или в `@DefaultValue`
- [ ] Тип (string, int, duration, list) совпадает
- [ ] Профиль-specific значения — если документ различает dev/prod
- [ ] Связь config → behavior: класс, читающий ключ, использует значение как описано

---

## E. Feature toggles

### E.1 Где искать

- Toggle enums, feature flag registries
- `@ConditionalOnProperty`, `@FeatureToggle`
- LaunchDarkly / Unleash / custom `FeatureService`
- Config keys вида `feature.*.enabled`

### E.2 Чеклист

- [ ] Имя toggle в документе = константа в коде
- [ ] Default (on/off) совпадает
- [ ] Ветка «если включён» / «если выключен» — найти if/switch и сравнить поведение
- [ ] Scope (per-user, global, per-tenant) — если заявлен

---

## F. Поведение и алгоритмы

### F.1 Классы и методы

- [ ] Класс существует
- [ ] Метод существует; параметры и return type не противоречат описанию
- [ ] Документ не ссылается на удалённый/deprecated API без пометки

### F.2 Control flow

- [ ] Порядок проверок (validation → filter → map) как в коде
- [ ] Early return / continue — те же условия
- [ ] Fallback (default comment, default type) — как в коде

### F.3 Observability

- [ ] Metric names / labels — Micrometer, Prometheus constants
- [ ] Log messages (WARN/ERROR) — строковые константы или i18n keys
- [ ] Trace/span names — если описаны

### F.4 Ограничения «код не меняется»

Если документ заявляет отсутствие изменений Java:

- [ ] Grep по ключевым словам фичи в `repositories/` — нет новых классов/методов под эту фичу
- [ ] Изменения только в migrations/config — согласовано с документом

---

## G. Формат доказательств (evidence)

Каждая находка в отчёте должна содержать (текст полей — **на русском**, кроме цитат из кода):

```
Раздел документа: §4.2.3, таблица `example_table`, колонка `status`
Утверждение: «INSERT устанавливает status = 'ACTIVE'»
Код: repositories/<service>/src/main/resources/db/changelog/.../001.xml:42-58
Доказательство: <фрагмент SQL или Java>
Статус: MISMATCH — в коде используется 'ENABLED', а не 'ACTIVE'
```

---

## H. Что не проверять этим скиллом

- Соответствие брифу / бизнес-постановке (это `/check-feature`)
- Полноту структуры каталога (это `/check-feature`)

## I. Выходной файл

| Параметр | Значение |
|----------|----------|
| Путь | `Feature-writing/<slug>/<slug>-code-alignment.md` |
| Парный документ | `Feature-writing/<slug>/<slug>.md` |
| Язык отчёта | **русский** (статусы и идентификаторы кода — как в исходниках) |
| Повторный прогон | перезапись того же файла |
| Диалог | только краткая сводка на русском + путь к файлу |

Не редактировать `<slug>.md` — только создавать/обновлять `<slug>-code-alignment.md`.
