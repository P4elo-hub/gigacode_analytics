"""Читает kb-writing-kits/spec-catalog.yaml: блоки, профили, kit."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from artifact_paths import workspace_root

CATALOG_RELATIVE = Path("kb-writing-kits") / "spec-catalog.yaml"


def catalog_path(root: Path | None = None) -> Path:
    return (root or workspace_root()) / CATALOG_RELATIVE


@lru_cache(maxsize=4)
def load_catalog(root_str: str | None = None) -> dict:
    path = catalog_path(Path(root_str) if root_str else None)
    if not path.is_file():
        raise FileNotFoundError(f"нет каталога блоков: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ImportError:
        data = parse_simple_yaml(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"каталог {path} должен быть mapping")
    return data


def catalog_blocks(root: Path | None = None) -> list[dict]:
    return list(load_catalog(_root_key(root)).get("blocks") or [])


def parent_headers(root: Path | None = None) -> dict[str, str]:
    raw = load_catalog(_root_key(root)).get("parent_headers") or {}
    return {str(key): str(value) for key, value in raw.items()}


def parent_order(root: Path | None = None) -> list[str]:
    raw = load_catalog(_root_key(root)).get("parent_order") or []
    return [str(item) for item in raw]


def default_profile_name(root: Path | None = None) -> str:
    return str(load_catalog(_root_key(root)).get("default_profile") or "sihist")


def profile_sections(root: Path | None = None) -> dict[str, list[str]]:
    raw = load_catalog(_root_key(root)).get("profiles") or {}
    return {
        str(name): [str(section_id) for section_id in sections]
        for name, sections in raw.items()
    }


def extra_keywords(root: Path | None = None) -> dict[str, list[str]]:
    raw = load_catalog(_root_key(root)).get("extra_keywords") or {}
    return {
        str(section_id): [str(word) for word in words]
        for section_id, words in raw.items()
    }


def _root_key(root: Path | None) -> str | None:
    return str(root.resolve()) if root is not None else None


def parse_simple_yaml(text: str) -> object:
    """Подмножество YAML: mapping, list, quoted/plain scalars, комментарии."""
    rows: list[tuple[int, int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        indent = len(line) - len(line.lstrip(" "))
        stripped = _strip_inline_comment(line).strip()
        if not stripped or stripped.startswith("#"):
            continue
        rows.append((line_no, indent, stripped))
    value, index = _parse_value(rows, 0, 0)
    if index != len(rows):
        line_no = rows[index][0]
        raise ValueError(f"лишняя строка YAML около {line_no}")
    return value


def _parse_value(
    rows: list[tuple[int, int, str]],
    index: int,
    min_indent: int,
) -> tuple[object, int]:
    if index >= len(rows):
        return None, index
    _line_no, indent, content = rows[index]
    if indent < min_indent:
        return None, index
    if content.startswith("- "):
        return _parse_list(rows, index, indent)
    return _parse_mapping(rows, index, indent)


def _parse_mapping(
    rows: list[tuple[int, int, str]],
    index: int,
    indent: int,
) -> tuple[dict, int]:
    mapping: dict = {}
    while index < len(rows):
        line_no, line_indent, content = rows[index]
        if line_indent < indent or content.startswith("- "):
            break
        if line_indent > indent:
            raise ValueError(f"неверный отступ YAML на строке {line_no}")
        key, sep, rest = content.partition(":")
        if not sep:
            raise ValueError(f"ожидался ключ: на строке {line_no}")
        key = _unquote(key.strip())
        rest = rest.strip()
        index += 1
        if rest:
            mapping[key] = _parse_scalar(rest)
            continue
        if index >= len(rows) or rows[index][1] <= indent:
            mapping[key] = None
            continue
        child, index = _parse_value(rows, index, indent + 1)
        mapping[key] = child
    return mapping, index


def _parse_list(
    rows: list[tuple[int, int, str]],
    index: int,
    indent: int,
) -> tuple[list, int]:
    items: list = []
    while index < len(rows):
        line_no, line_indent, content = rows[index]
        if line_indent < indent or not content.startswith("- "):
            break
        if line_indent > indent:
            raise ValueError(f"неверный отступ списка YAML на строке {line_no}")
        payload = content[2:].strip()
        index += 1
        if payload == "":
            child, index = _parse_value(rows, index, indent + 1)
            items.append(child)
            continue
        if ":" in payload and not _is_quoted(payload):
            key, _sep, rest = payload.partition(":")
            item = {_unquote(key.strip()): _parse_scalar(rest.strip()) if rest.strip() else None}
            while index < len(rows) and rows[index][1] > indent and not rows[index][2].startswith("- "):
                nested, index = _parse_mapping(rows, index, rows[index][1])
                item.update(nested)
            items.append(item)
            continue
        items.append(_parse_scalar(payload))
    return items, index


def _strip_inline_comment(line: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            if index == 0 or line[index - 1].isspace():
                return line[:index]
    return line


def _is_quoted(value: str) -> bool:
    return len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]


def _unquote(value: str) -> str:
    if _is_quoted(value):
        return value[1:-1]
    return value


def _parse_scalar(raw: str) -> object:
    if raw in ("~", "null", "Null", "NULL"):
        return None
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    if _is_quoted(raw):
        return raw[1:-1]
    return raw
