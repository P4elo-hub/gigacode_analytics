---
name: integration-analysis
description: >-
  Пишет контракт 4.1.1 / 4.1.2. Форма — integration-standard-kit выбранного протокола.
user-invocable: false
disable-model-invocation: true
---

# integration-analysis

Маршрут блока `integration`. Форма — template/gate выбранного протокола в kit.

База: `kb-writing-kits/kits/integration/methodology/integration-standard-kit/`

Skill kit: `skills/integration-analysis/SKILL.md`

Протокол задаёт оркестратор (`--protocol`):

| Протокол | Template | Example | Gate |
|----------|----------|---------|------|
| REST | `templates/rest-endpoint.template.md` | `examples/rest-integration-example.md` | `quality-gates/rest-review.yaml` |
| gRPC | `templates/grpc-service.template.md` | `examples/grpc-service-example.md` | `quality-gates/grpc-review.yaml` |
| GraphQL | `templates/graphql-operation.template.md` | `examples/graphql-operation-example.md` | `quality-gates/graphql-review.yaml` |
| SOAP | `templates/soap-operation.template.md` | `examples/soap-operation-example.md` | `quality-gates/soap-review.yaml` |
| Async | `templates/async-message.template.md` | `examples/async-message-example.md` | `quality-gates/async-review.yaml` |

Протокол не задан → REST, если в брифе нет Kafka/события.

1. Прочитай skill kit + template + example + gate **этого** протокола целиком.
2. Пиши ровно по ним. Не добавляй формат (JSON/YAML) сверх template.
3. Нет факта → `[GAP-...]`. Верни только Markdown блока `integration`.
