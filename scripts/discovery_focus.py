"""Фокус discovery: какие якоря искать в find-context по типу фичи."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FOCUS_INTEGRATION = "integration"
FOCUS_DATA = "data"
FOCUS_MIXED = "mixed"
FOCUS_GENERAL = "general"

INTEGRATION_KEYWORDS = (
    "grpc", "proto", "protobuf", "rpc", "rest", "graphql", "soap", "kafka",
    "endpoint", "openapi", "swagger", "контракт",
)
DATA_KEYWORDS = (
    "миграц", "liquibase", "changelog", "ddl", "таблиц", "колонк",
    "entity", "схема бд", "модель данных", "db-export",
)

INTEGRATION_SEED_TERMS = ("proto", "rpc", "grpc")
DATA_SEED_TERMS = ("liquibase", "changelog", "migration", "ddl")

PATH_BONUS_PROTO = 16
PATH_BONUS_RPC = 10
PATH_BONUS_MIGRATION = 14
PATH_BONUS_SQL = 10
PATH_BONUS_DB_EXPORT = 8

PROTO_SUFFIX = ".proto"
SQL_SUFFIX = ".sql"
MIGRATION_PATH_MARKERS = ("liquibase", "changelog", "migration", "migrations")
RPC_PATH_MARKERS = ("grpc", "proto", "rpc")


@dataclass(frozen=True)
class DiscoveryFocus:
    kind: str
    seed_terms: tuple[str, ...]
    open_first: tuple[str, ...]
    required_anchors: tuple[str, ...]


_FOCUS_INTEGRATION = DiscoveryFocus(
    FOCUS_INTEGRATION,
    INTEGRATION_SEED_TERMS,
    ("файлы `*.proto`", "RPC / service в `repositories/`"),
    ("service", "rpc", "message", "поля proto"),
)
_FOCUS_DATA = DiscoveryFocus(
    FOCUS_DATA,
    DATA_SEED_TERMS,
    ("liquibase / changelog", "DDL в `db-export/`"),
    ("таблица", "колонка", "changeset"),
)
_FOCUS_MIXED = DiscoveryFocus(
    FOCUS_MIXED,
    INTEGRATION_SEED_TERMS + DATA_SEED_TERMS,
    _FOCUS_INTEGRATION.open_first + _FOCUS_DATA.open_first,
    _FOCUS_INTEGRATION.required_anchors + _FOCUS_DATA.required_anchors,
)
_FOCUS_GENERAL = DiscoveryFocus(
    FOCUS_GENERAL,
    INTEGRATION_SEED_TERMS,
    ("`*.proto` и RPC, если есть в выдаче", "DDL / liquibase, если есть в выдаче"),
    ("контракт: service / rpc / message", "данные: таблица / колонка"),
)


def detect_focus(brief: str) -> DiscoveryFocus:
    lower = brief.lower()
    has_integration = any(keyword in lower for keyword in INTEGRATION_KEYWORDS)
    has_data = any(keyword in lower for keyword in DATA_KEYWORDS)
    if has_integration and has_data:
        return _FOCUS_MIXED
    if has_integration:
        return _FOCUS_INTEGRATION
    if has_data:
        return _FOCUS_DATA
    return _FOCUS_GENERAL


def suggested_extra_terms(focus: DiscoveryFocus) -> str:
    return " ".join(focus.seed_terms)


def path_score_bonus(path: Path, focus: DiscoveryFocus) -> int:
    """Бонус только если файл уже совпал по терминам брифа (вызывающий проверяет score)."""
    path_lower = str(path).lower()
    suffix = path.suffix.lower()
    bonus = 0
    applies_integration = focus.kind in {FOCUS_INTEGRATION, FOCUS_MIXED, FOCUS_GENERAL}
    applies_data = focus.kind in {FOCUS_DATA, FOCUS_MIXED, FOCUS_GENERAL}
    if applies_integration:
        if suffix == PROTO_SUFFIX:
            bonus += PATH_BONUS_PROTO
        if any(marker in path_lower for marker in RPC_PATH_MARKERS):
            bonus += PATH_BONUS_RPC
    if applies_data:
        if suffix == SQL_SUFFIX:
            bonus += PATH_BONUS_SQL
        if any(marker in path_lower for marker in MIGRATION_PATH_MARKERS):
            bonus += PATH_BONUS_MIGRATION
        if "db-export" in path_lower:
            bonus += PATH_BONUS_DB_EXPORT
    return bonus


def focus_instruction_lines(focus: DiscoveryFocus) -> list[str]:
    open_first = "; ".join(focus.open_first)
    anchors = ", ".join(focus.required_anchors)
    extra_terms = suggested_extra_terms(focus)
    return [
        "## Фокус поиска",
        "",
        f"Тип фичи: `{focus.kind}`.",
        f"Сначала открой: {open_first}.",
        f"Обязательные якоря в CONTEXT_DOC: {anchors}.",
        f"Мало якорей в выдаче → перезапусти с `--terms \"{extra_terms}\"` "
        "и доменными именами сервисов/полей.",
        "Нет файла с якорем → `Q-XX`, не выдумывай контракт или схему.",
        "",
    ]
