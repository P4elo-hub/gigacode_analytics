<!--
Imported from: nfr-standard-kit/templates\configuration.template.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### NFR — [Название фичи] (Конфигурация)

### Настройки и конфигурация

Классификация (справочно — при необходимости вынести в отдельные таблицы):
- Уровень безопасности: `public` / `internal` / `secret`
- Частота изменения: `static` / `dynamic` / `runtime`
- Область: `global` / `environment-specific` / `instance-specific`

| Параметр | Тип | Уровень | Частота | Область | Хранение | По умолчанию | Описание | Валидация | Влияние при изменении | Процедура отката |
|----------|-----|---------|---------|---------|----------|-------------|----------|-----------|----------------------|------------------|
| [ключ] | [тип] | [уровень] | [частота] | [область] | [ConfigMap / Secrets / Vault / БД / env] | [default] | [описание] | [min/max/pattern] | [влияние] | [откат] |

Способы хранения (если нужен отдельный блок):
| Способ | Когда использовать | Примеры |
|--------|-------------------|---------|
| [способ] | [когда] | [примеры ключей] |

Процедура изменения (если нужен отдельный блок):
| Тип параметра | Процедура изменения | Кто изменяет | Требуется согласование |
|---------------|---------------------|--------------|------------------------|
| [static/dynamic/runtime] | [как менять] | [роль] | [да/нет] |
