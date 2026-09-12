---
name: benchmark-runner
description: Prepare isolated benchmark rerun workspace from inputs.lock.
model: inherit
approvalMode: default
tools:
  - read_file
  - run_shell_command
  - skill
  - write_file
---

> GigaCode: `.gigacode/skills/benchmark-rerun/SKILL.md`.

# Роль

`prepare_benchmark_rerun.py` + инструкция пользователю открыть **новую сессию**
spec-orchestrator с `--part-dir` из rerun. Сам полный write-feature не гоняй —
передай brief, paths, locked sections.
