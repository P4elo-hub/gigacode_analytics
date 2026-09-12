<!--
Imported from: integration-standard-kit/examples\grpc-service-example.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### Пример gRPC endpoint (согласно стандартам СТД-ИНТ-01, СТД-GRPC-01-07)

**gRPC сервис:** DomainRecordsService  
**Метод:** SearchDomainRecords

**Общая информация (СТД-ИНТ-01):**
| Параметр | Значение |
|----------|----------|
| Назначение | Получение истории событий по счёту клиента |
| Система-источник | Mobile App / Web App (BFF) |
| Система-получатель | Operations Service |
| Тип интеграции | Синхронная |
| Протокол | gRPC (HTTP/2) |
| Направление | Однонаправленная (Unary RPC) |
| Package | broker.operations.v1 |
| Service | DomainRecordsService |
| Метод | SearchDomainRecords |
| Тип RPC | Unary |
| SLA | p95 < 300ms, p99 < 500ms |

**Request Metadata (gRPC Headers) (СТД-ЗАГОЛ-01):**

> В gRPC заголовки передаются через **metadata** — пары ключ-значение, аналог HTTP headers. Metadata передаётся вместе с каждым RPC вызовом, но не является частью protobuf-контракта (`.proto` файла).

| Metadata Key | Обязат. | Описание | Пример |
|--------------|---------|----------|--------|
| authorization | Да | Bearer JWT токен | Bearer demo-header.demo-payload.demo-signature |
| x-request-id | Да | UUID для трассировки (distributed tracing) | 7c9e6679-7425-40de-944b-e07fc1f90ae7 |
| x-client-id | Да | Идентификатор клиентского приложения | mobile-app-ios |
| x-idempotency-key | Нет | Ключ идемпотентности (для мутаций) | — |

**Response Metadata (gRPC Trailing Headers) (СТД-ЗАГОЛ-02):**

> gRPC возвращает метаданные в **initial metadata** (до тела ответа) и **trailing metadata** (после тела, содержит grpc-status). Trailing metadata — основной механизм передачи статуса.

| Metadata Key | Описание | Пример |
|--------------|----------|--------|
| x-request-id | Echo request ID | 7c9e6679-7425-40de-944b-e07fc1f90ae7 |
| grpc-status | Код статуса gRPC | 0 (OK) |
| grpc-message | Сообщение об ошибке (при ошибке) | — |
| x-ratelimit-limit | Лимит запросов | 500 |
| x-ratelimit-remaining | Осталось запросов | 495 |

**Proto Definition (СТД-GRPC-01, СТД-GRPC-06):**
```protobuf
syntax = "proto3";
package broker.operations.v1;

import "google/protobuf/timestamp.proto";

service DomainRecordsService {
  rpc SearchDomainRecords(SearchDomainRecordsRequest)
      returns (SearchDomainRecordsResponse);
}

message SearchDomainRecordsRequest {
  string account_id = 1;           // UUID брокерского счёта
  google.protobuf.Timestamp from = 2;  // Начало периода
  google.protobuf.Timestamp to = 3;    // Конец периода
  repeated OperationType types = 4;    // Фильтр по типам
  int32 limit = 5;                 // Лимит записей (1-1000)
  string cursor = 6;               // Курсор пагинации
}

message SearchDomainRecordsResponse {
  repeated Operation operations = 1;  // Список событий
  string next_cursor = 2;             // Курсор следующей страницы
  bool has_more = 3;                  // Есть ещё данные
}

message Operation {
  string operation_id = 1;            // UUID события
  OperationType type = 2;             // Тип события
  OperationStatus status = 3;         // Статус события
  string instrument_id = 4;           // FIGI инструмента
  MoneyValue amount = 5;              // Сумма события
  google.protobuf.Timestamp date = 6; // Дата события
  string description = 7;             // Описание события
}

message MoneyValue {
  string currency = 1;                // Валюта (ISO 4217: RUB, USD, EUR)
  int64 units = 2;                    // Целая часть суммы
  int32 nano = 3;                     // Дробная часть (10^-9)
}

enum OperationType {
  OPERATION_TYPE_UNSPECIFIED = 0;     // Значение по умолчанию
  OPERATION_TYPE_BUY = 1;            // Покупка ценных бумаг
  OPERATION_TYPE_SELL = 2;           // Продажа ценных бумаг
  OPERATION_TYPE_DIVIDEND = 3;       // Начисление дивидендов
  OPERATION_TYPE_COUPON = 4;         // Купонный доход по облигациям
  OPERATION_TYPE_TAX = 5;            // Удержание налога
  OPERATION_TYPE_COMMISSION = 6;     // Комиссия брокера
}

enum OperationStatus {
  ITEM_STATUS_UNSPECIFIED = 0;   // Значение по умолчанию
  ITEM_STATUS_PROGRESS = 1;     // В процессе выполнения
  ITEM_STATUS_SUCCESS = 2;      // Успешно выполнена
  ITEM_STATUS_CANCELED = 3;     // Отменена
}
```

**Параметры запроса (СТД-GRPC-03, СТД-СИНХ-ПАР-08):**
| Параметр | Тип | Обязат. | Описание | Валидация | По умолч. | Пример |
|----------|-----|---------|----------|-----------|-----------|--------|
| account_id | string | Да | UUID брокерского счёта | minLength: 36, maxLength: 36, format: uuid | — | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |
| from | Timestamp | Да | Начало периода | format: timestamp, <= to | — | {"seconds": 1704067200} |
| to | Timestamp | Да | Конец периода | format: timestamp, >= from, <= now | — | {"seconds": 1706745600} |
| types | repeated OperationType | Нет | Фильтр по типам событий | minItems: 0, maxItems: 7, uniqueItems: true, enum: [0-6] | [] | [1, 2] |
| limit | int32 | Нет | Лимит записей на страницу | minimum: 1, maximum: 1000 | 50 | 100 |
| cursor | string | Условно* | Курсор пагинации | minLength: 1, maxLength: 256, format: base64 | — | eyJvZmZzZXQiOjUwfQ== |

**Условия обязательности:**
| Параметр | Условие обязательности |
|----------|----------------------|
| cursor | Обязателен при запросе следующей страницы (has_more = true в предыдущем ответе) |

**Enum: OperationType (СТД-GRPC-04):**
| Значение | Код | Описание |
|----------|-----|----------|
| OPERATION_TYPE_UNSPECIFIED | 0 | Значение по умолчанию |
| OPERATION_TYPE_BUY | 1 | Покупка ценных бумаг |
| OPERATION_TYPE_SELL | 2 | Продажа ценных бумаг |
| OPERATION_TYPE_DIVIDEND | 3 | Начисление дивидендов |
| OPERATION_TYPE_COUPON | 4 | Купонный доход по облигациям |
| OPERATION_TYPE_TAX | 5 | Удержание налога |
| OPERATION_TYPE_COMMISSION | 6 | Комиссия брокера |

**Параметры ответа (СТД-GRPC-03, СТД-СИНХ-ПАР-05, СТД-СИНХ-ПАР-08):**
| Параметр | Тип | Обязат. | Описание | Валидация | По умолч. | Пример | Маппинг |
|----------|-----|---------|----------|-----------|-----------|--------|---------|
| operations | repeated Operation | Да | Массив событий | minItems: 0, maxItems: 1000 | [] | `[{ "operation_id": "op-12345678-90ab-cdef-1234-567890abcdef", "type": "OPERATION_TYPE_BUY", "status": "ITEM_STATUS_SUCCESS" }]` | — |
| ├─ operation_id | string | Да | UUID события | minLength: 36, maxLength: 36, format: uuid | — | op-12345678-90ab-cdef-1234-567890abcdef | Operations DB → operation_id |
| ├─ type | OperationType | Да | Тип события | enum: [0-6] | — | OPERATION_TYPE_BUY | Operations DB → op_type_code |
| ├─ status | OperationStatus | Да | Статус события | enum: [0-3] | — | ITEM_STATUS_SUCCESS | Operations DB → op_status |
| ├─ instrument_id | string | Да | FIGI инструмента | minLength: 1, maxLength: 12 | — | BBG004730N88 | Instruments DB → figi |
| ├─ amount | MoneyValue | Да | Сумма события | required: [currency, units, nano] | — | `{ "currency": "RUB", "units": 15000, "nano": 500000000 }` | Operations DB → amount |
| │ ├─ currency | string | Да | Валюта | minLength: 3, maxLength: 3, pattern: `^[A-Z]{3}$` | — | RUB | Operations DB → currency_code |
| │ ├─ units | int64 | Да | Целая часть | minimum: 0 | — | 15000 | Operations DB → amount_units |
| │ └─ nano | int32 | Да | Дробная часть (10⁻⁹) | minimum: 0, maximum: 999999999 | — | 500000000 | Operations DB → amount_nano |
| ├─ date | Timestamp | Да | Дата события | format: timestamp | — | {"seconds": 1704153600} | Operations DB → created_ts |
| └─ description | string | Нет | Описание | maxLength: 500 | "" | Покупка 10 акций Сбербанк | Operations DB → description |
| next_cursor | string | Да | Курсор следующей страницы | maxLength: 256 | "" | eyJvZmZzZXQiOjUwfQ== | Вычисляется (offset) |
| has_more | bool | Да | Флаг продолжения | — | false | true | COUNT(*) > offset + limit |

**JSON Schema запроса (SearchDomainRecordsRequest):**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SearchDomainRecordsRequest",
  "type": "object",
  "required": ["account_id", "from", "to"],
  "additionalProperties": false,
  "properties": {
    "account_id": {
      "type": "string",
      "description": "UUID брокерского счёта",
      "minLength": 36,
      "maxLength": 36,
      "format": "uuid"
    },
    "from": {
      "type": "object",
      "description": "Начало периода (Timestamp)",
      "required": ["seconds"],
      "properties": {
        "seconds": { "type": "integer", "description": "Unix timestamp" },
        "nanos": { "type": "integer", "minimum": 0, "maximum": 999999999 }
      }
    },
    "to": {
      "type": "object",
      "description": "Конец периода (Timestamp)",
      "required": ["seconds"],
      "properties": {
        "seconds": { "type": "integer", "description": "Unix timestamp" },
        "nanos": { "type": "integer", "minimum": 0, "maximum": 999999999 }
      }
    },
    "types": {
      "type": "array",
      "description": "Фильтр по типам событий",
      "items": { "type": "integer", "enum": [0, 1, 2, 3, 4, 5, 6] },
      "minItems": 0,
      "maxItems": 7,
      "uniqueItems": true,
      "default": []
    },
    "limit": {
      "type": "integer",
      "description": "Лимит записей на страницу",
      "minimum": 1,
      "maximum": 1000,
      "default": 50
    },
    "cursor": {
      "type": "string",
      "description": "Курсор пагинации (обязателен при запросе следующей страницы)",
      "minLength": 1,
      "maxLength": 256,
      "format": "base64"
    }
  }
}
```

**JSON Schema ответа (SearchDomainRecordsResponse):**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SearchDomainRecordsResponse",
  "type": "object",
  "required": ["operations", "next_cursor", "has_more"],
  "additionalProperties": false,
  "properties": {
    "operations": {
      "type": "array",
      "description": "Список событий",
      "minItems": 0,
      "maxItems": 1000,
      "items": {
        "$ref": "#/definitions/Operation"
      }
    },
    "next_cursor": {
      "type": "string",
      "description": "Курсор следующей страницы",
      "maxLength": 256,
      "default": ""
    },
    "has_more": {
      "type": "boolean",
      "description": "Флаг наличия следующей страницы",
      "default": false
    }
  },
  "definitions": {
    "Operation": {
      "type": "object",
      "required": ["operation_id", "type", "status", "instrument_id", "amount", "date"],
      "additionalProperties": false,
      "properties": {
        "operation_id": {
          "type": "string",
          "description": "UUID события",
          "minLength": 36,
          "maxLength": 36,
          "format": "uuid"
        },
        "type": {
          "type": "string",
          "description": "Тип события",
          "enum": [
            "OPERATION_TYPE_UNSPECIFIED",
            "OPERATION_TYPE_BUY",
            "OPERATION_TYPE_SELL",
            "OPERATION_TYPE_DIVIDEND",
            "OPERATION_TYPE_COUPON",
            "OPERATION_TYPE_TAX",
            "OPERATION_TYPE_COMMISSION"
          ]
        },
        "status": {
          "type": "string",
          "description": "Статус события",
          "enum": [
            "ITEM_STATUS_UNSPECIFIED",
            "ITEM_STATUS_PROGRESS",
            "ITEM_STATUS_SUCCESS",
            "ITEM_STATUS_CANCELED"
          ]
        },
        "instrument_id": {
          "type": "string",
          "description": "FIGI инструмента",
          "minLength": 1,
          "maxLength": 12
        },
        "amount": {
          "$ref": "#/definitions/MoneyValue"
        },
        "date": {
          "type": "object",
          "description": "Дата события (Timestamp)",
          "required": ["seconds"],
          "properties": {
            "seconds": { "type": "integer" },
            "nanos": { "type": "integer", "minimum": 0, "maximum": 999999999 }
          }
        },
        "description": {
          "type": "string",
          "description": "Описание события",
          "maxLength": 500,
          "default": ""
        }
      }
    },
    "MoneyValue": {
      "type": "object",
      "description": "Денежное значение",
      "required": ["currency", "units", "nano"],
      "additionalProperties": false,
      "properties": {
        "currency": {
          "type": "string",
          "description": "Валюта (ISO 4217)",
          "minLength": 3,
          "maxLength": 3,
          "pattern": "^[A-Z]{3}$"
        },
        "units": {
          "type": "integer",
          "description": "Целая часть суммы",
          "minimum": 0
        },
        "nano": {
          "type": "integer",
          "description": "Дробная часть (10^-9)",
          "minimum": 0,
          "maximum": 999999999
        }
      }
    }
  }
}
```

**Пример запроса и ответа — Happy Path:**
```json
// REQUEST
{
  "account_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "from": { "seconds": 1704067200 },
  "to": { "seconds": 1706745600 },
  "types": [1, 2],
  "limit": 50
}
```

```json
// RESPONSE (gRPC Status: OK)
{
  "operations": [
    {
      "operation_id": "op-12345678-90ab-cdef-1234-567890abcdef",
      "type": "OPERATION_TYPE_BUY",
      "status": "ITEM_STATUS_SUCCESS",
      "instrument_id": "BBG004730N88",
      "amount": { "currency": "RUB", "units": 15000, "nano": 500000000 },
      "date": { "seconds": 1704153600 },
      "description": "Покупка 10 акций Сбербанк"
    }
  ],
  "next_cursor": "eyJvZmZzZXQiOjUwfQ==",
  "has_more": true
}
```

**Пограничный случай: Пустой результат (нет событий за период):**
```json
// REQUEST
{
  "account_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "from": { "seconds": 946684800 },
  "to": { "seconds": 946771200 },
  "limit": 100
}
```

```json
// RESPONSE (gRPC Status: OK)
{
  "operations": [],
  "next_cursor": "",
  "has_more": false
}
```
> **Примечание:** При отсутствии данных возвращается пустой массив `operations: []`, а не `null`. `has_more: false` и `next_cursor` — пустая строка.

**Коды ошибок (СТД-GRPC-05):**
| gRPC код | Название | Описание | Условие |
|----------|----------|----------|---------|
| 3 | INVALID_ARGUMENT | Неверные входные данные | Невалидный UUID, from > to |
| 5 | NOT_FOUND | Счёт не найден | account_id не существует |
| 7 | PERMISSION_DENIED | Нет доступа к счёту | Чужой счёт |
| 16 | UNAUTHENTICATED | Требуется аутентификация | Нет токена |
| 8 | RESOURCE_EXHAUSTED | Превышен лимит запросов | Rate limit |
| 13 | INTERNAL | Внутренняя ошибка | Сбой сервиса |
| 14 | UNAVAILABLE | Сервис недоступен | Maintenance |

