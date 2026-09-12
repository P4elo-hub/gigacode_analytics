# Kit: Interface Contract

## Назначение

Для любых контрактов, через которые функционал вызывается, принимает события/данные или отдает результат. REST, gRPC, WebSocket и event/message - только примеры, а не закрытый список; сюда же относятся GraphQL, SOAP/WSDL, AsyncAPI, Kafka/RabbitMQ/JMS/SQS/PubSub topics, batch/file/SFTP layouts, webhooks/callbacks, CDC/outbox/inbox, CLI/native protocols и frontend/mobile bridge contracts, если они есть в источниках.

## Reader-first обязательство

Применяй этот kit только вместе с `10-Governance/reader-first-writing-standard.md`. Постоянная страница сначала объясняет читателю назначение, участников, вход, результат и текущее поведение простым языком. Технические имена допустимы только после пояснения их роли; если на странице больше трех технических названий, добавь раздел `Как читать технические названия`.
## Evidence pack

- Protocol/transport.
- Direction: incoming/outgoing/internal.
- Method/path/RPC/message/topic/query/mutation/SOAP action/file layout/webhook/CDC stream.
- Версия или legacy/platform variant.
- Headers, metadata, session context, path/query/body/event/file fields.
- Поля ответа.
- Обязательность, defaults, nullable, validation, schema constraints.
- Error behavior.
- Примеры запроса/ответа из кода, proto, tests или аналитики.
- Compatibility notes.

Для deep-detail intent `full-interface-contract-field-matrix` evidence pack дополнительно должен собрать:

- матрицу path/query/body/metadata/request/response/event/file fields;
- типы, nullable, required/optional, default и validation, если они прямо подтверждены;
- mapping между DTO/proto/model/response;
- error response shape и error codes, если они подтверждены;
- версии, legacy/platform/mobile/web отличия;
- примеры из tests/fixtures или аналитики.

Обязательность поля нельзя выводить только из имени класса или наличия поля в DTO. Нужен proto/OpenAPI/GraphQL/AsyncAPI/Avro/JSON Schema/XSD/WSDL annotation, validation, Kotlin/Java nullability, тест, аналитика или другое прямое evidence.

## Постоянная страница

Нужны назначение интерфейса, кто вызывает и кто обслуживает, контракт вызова, поля запроса и ответа, ошибки, session/auth context, версионность, совместимость и подтвержденный пример.

Для full contract page таблицы полей допустимы, но перед ними должно быть читательское объяснение назначения контракта, направления вызова и результата.
## Полный методологический слой

Этот kit использует не только краткий checklist выше. В подпапке methodology/ лежат адаптированные материалы исходных feature methodology kits: README, templates, schemas, quality gates, examples и skill-инструкции.

При выполнении команд 12, 13 и 14 агент должен читать эти материалы как расширенный профиль kit-а и применять их к current-state базе знаний.

Подключенные source kits:

- methodology/integration-standard-kit/

Правило адаптации: использовать все требования к структуре, детализации, примерам, матрицам, диаграммам, проверкам и evidence, но не переносить в постоянную страницу future/change-management слой: TO BE, rollout/rollback, будущие требования, design proposals, GAP-*, ASM-*, DESIGN-* как читательский текст. Такие элементы фиксируются только в рабочем слое как gaps или не используются.
