# Qwen Code layout

Порт аналитического пайплайна SIHIST с OpenCode на [Qwen Code](https://github.com/QwenLM/qwen-code).

Запуск из корня workspace:

```bash
qwen
```

Дальше те же слэш-команды — **точки входа**, не чеклист.

Обычный старт: бриф в чате или `/find-context <бриф>` / `/write-feature <бриф>`.
Основная сессия — оркестратор: сама вызывает субагентов и идёт к next step.
Человек отвечает только на вопросы по существу (блоки, гэпы, CH, alignment).

| Было (OpenCode) | Стало (Qwen Code) |
|-----------------|-------------------|
| `opencode.json` | `.qwen/settings.json` |
| `.opencode/commands/` | `.qwen/commands/` (`{{args}}`) |
| `.opencode/agents/` | `.qwen/agents/` |
| `.opencode/skills/` | `.qwen/skills/` (`user-invocable: false`) |
| `.opencode/rules/` | `.qwen/rules/` |
| `default_agent: spec-orchestrator` | `QWEN.md` + `AGENTS.md` |

Каталог `.opencode/` оставлен как наследие: пайплайн для Qwen Code живёт здесь.
Python-скрипты в `scripts/` не менялись.

`analytics/`, `db-export/` и `repositories/` в `.gitignore`. В `settings.base.json`
стоит `respectGitIgnore: false`, иначе CLI не увидит эти папки. Игнор для поиска —
`.qwenignore` (node_modules, кэш).

**Настройки CLI:** не правьте `settings.json` вручную. Permissions и model — в
`settings.base.json`, hooks — в `settings.hooks.json`. Сборка:

```bash
python3 scripts/build_cli_settings.py
```
