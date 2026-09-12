---
name: review-capturer
description: Capture human review themes after gold sync into human-review.md.
model: inherit
approvalMode: default
tools:
  - read_file
  - run_shell_command
  - skill
  - write_file
---

> GigaCode: `.gigacode/skills/capture-review/SKILL.md`.

# Роль

После правок пользователя: sync gold + структурированный `human-review.md`.
