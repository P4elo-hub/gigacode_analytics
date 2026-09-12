# GigaCode layout

Порт аналитического пайплайна SIHIST с OpenCode/Qwen на [GigaCode CLI](https://gitverse.ru/docs/ai/gigacode-on-gitverse/gigacode-agent) (форк qwen-code).

Запуск из корня workspace:

```bash
gigacode
```

Дальше те же слэш-команды — **точки входа**, не чеклист.

Обычный старт: бриф в чате или `/find-context <бриф>` / `/write-feature <бриф>`.
Основная сессия — оркестратор: сама вызывает субагентов и идёт к next step.
Человек отвечает только на вопросы по существу (блоки, гэпы, CH, alignment).

| Было (OpenCode) | Стало (GigaCode) |
|-----------------|-------------------|
| `opencode.json` | `.gigacode/settings.json` |
| `.opencode/commands/` | `.gigacode/commands/` (`{{args}}`) |
| `.opencode/agents/` | `.gigacode/agents/` |
| `.opencode/skills/` | `.gigacode/skills/` (`user-invocable: false`) |
| `.opencode/rules/` | `.gigacode/rules/` |
| `default_agent: spec-orchestrator` | `GIGACODE.md` + `AGENTS.md` |

Каталоги `.qwen/` и `.opencode/` — наследие; пайплайн для GigaCode живёт в `.gigacode/`.
Python-скрипты в `scripts/` не менялись.

`analytics/`, `db-export/` и `repositories/` в `.gitignore`. В `settings.base.json`
стоит `respectGitIgnore: false`, иначе CLI не увидит эти папки. Игнор для поиска —
`.gigacodeignore` (node_modules, кэш).

**Настройки CLI:** не правьте `settings.json` вручную. Permissions — в
`settings.base.json`, hooks — в `settings.hooks.json`. Сборка:

```bash
python3 scripts/build_cli_settings.py
```
