#!/usr/bin/env python3
"""find-context — поиск релевантных документов и кода по брифу фичи.

Детерминированный helper для команды `find-context`. По тексту брифа находит и
ранжирует кандидатов в разрешённых областях базы знаний и собирает discovery-пакет:
бриф, поисковые термины, таблицы кандидатов (документы / код / данные / доп.
материалы) и скелет выходного документа-контекста.

Области поиска:
- аналитика (Confluence, фичи): analytics/;
- готовые спецификации фич: Feature-writing/ (Markdown);
- код и контракты: repositories/ (рекурсивно по всем сервисам);
- данные: db-export/;
- дополнительные материалы: auxiliary/ (если есть).

Без внешних зависимостей: только стандартная библиотека.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from discovery_focus import (
    detect_focus,
    focus_instruction_lines,
    path_score_bonus,
)

# --------------------------------------------------------------------------- #
# Конфигурация областей поиска
# --------------------------------------------------------------------------- #

FEATURE_WRITING_DIR = "Feature-writing"

DOC_ROOTS = [
    FEATURE_WRITING_DIR,
]

CODE_ROOT = "repositories"
DATA_ROOT = "db-export"
ANALYTICS_ROOT = "analytics"
AUX_ROOT = "auxiliary"

DOC_EXTENSIONS = {".md"}
CODE_EXTENSIONS = {
    ".java", ".kt", ".proto", ".sql", ".yml", ".yaml", ".xml", ".json",
    ".properties", ".conf", ".groovy", ".gradle", ".sh", ".xsd", ".cond",
    ".md", ".txt",
}
DATA_EXTENSIONS = {".md", ".sql", ".csv", ".json", ".txt"}
ANALYTICS_EXTENSIONS = {".md", ".drawio", ".puml", ".txt"}

SKIP_DIR_NAMES = {
    ".git", ".gradle", ".idea", "build", "out", "dist", "target", "bin",
    "node_modules", "__pycache__", ".devops", ".devsecops",
}

MAX_FILE_BYTES = 600_000
MAX_OCCURRENCES_PER_TERM = 25

# Русские и общие стоп-слова: не несут смысла для поиска.
STOPWORDS = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то",
    "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за",
    "бы", "по", "только", "ее", "мне", "было", "вот", "от", "меня", "еще",
    "нет", "о", "из", "ему", "теперь", "когда", "даже", "ну", "вдруг", "ли",
    "если", "уже", "или", "ни", "быть", "был", "него", "до", "вас", "нибудь",
    "опять", "уж", "вам", "ведь", "там", "потом", "себя", "ничего", "ей",
    "может", "они", "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя",
    "их", "чем", "была", "сам", "чтоб", "без", "будто", "чего", "раз", "тоже",
    "себе", "под", "будет", "ж", "тогда", "кто", "этот", "того", "потому",
    "этого", "какой", "совсем", "ним", "здесь", "этом", "один", "почти", "мой",
    "тем", "чтобы", "нее", "сейчас", "были", "куда", "зачем", "всех", "никогда",
    "можно", "при", "наконец", "два", "об", "другой", "хоть", "после", "над",
    "больше", "тот", "через", "эти", "нас", "про", "всего", "них", "какая",
    "много", "разве", "три", "эту", "моя", "впрочем", "хорошо", "свою", "этой",
    "перед", "иногда", "лучше", "чуть", "том", "нельзя", "такой", "им", "более",
    "всегда", "конечно", "всю", "между", "это", "нужно", "также", "которые",
    "которая", "который", "должна", "должен", "должно", "свой", "своих", "какие",
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "are",
    "be", "by", "with", "as", "at", "this", "that", "it", "from",
    "задача", "стоит", "нужно", "хочу", "сделать", "фича", "фичу", "фичи",
}


# --------------------------------------------------------------------------- #
# Извлечение поисковых терминов из брифа
# --------------------------------------------------------------------------- #

_TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_.]*")
_CAMEL_RE = re.compile(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])")


class Term:
    __slots__ = ("text", "weight")

    def __init__(self, text: str, weight: int):
        self.text = text
        self.weight = weight


def _camel_subwords(token: str) -> list[str]:
    parts = re.split(r"[._]", token)
    out: list[str] = []
    for part in parts:
        out.extend(m.group(0) for m in _CAMEL_RE.finditer(part))
    return [p for p in out if len(p) >= 3]


def extract_terms(brief: str, extra: str | None) -> list[Term]:
    """Возвращает уникальные термины с весами.

    Идентификаторы (camelCase, dotted, snake_case) и многословные технические
    токены весят больше, чем обычные слова.
    """
    seen: dict[str, Term] = {}

    def add(text: str, weight: int) -> None:
        key = text.lower()
        if len(key) < 3 or key in STOPWORDS or key.isdigit():
            return
        existing = seen.get(key)
        if existing is None or weight > existing.weight:
            seen[key] = Term(key, weight)

    source = brief
    if extra:
        source = f"{brief}\n{extra}"

    for raw in _TOKEN_RE.findall(source):
        is_identifier = ("." in raw or "_" in raw
                         or any(c.isupper() for c in raw[1:]))
        add(raw, weight=3 if is_identifier else 1)
        if is_identifier:
            for sub in _camel_subwords(raw):
                add(sub, weight=2)

    return sorted(seen.values(), key=lambda t: (-t.weight, t.text))


# --------------------------------------------------------------------------- #
# Поиск и скоринг
# --------------------------------------------------------------------------- #

class Hit:
    __slots__ = ("path", "score", "term_hits", "snippet")

    def __init__(self, path: Path, score: int, term_hits: list[str], snippet: str):
        self.path = path
        self.score = score
        self.term_hits = term_hits
        self.snippet = snippet


def _iter_files(root: Path, extensions: set[str]):
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_dir():
            if path.name in SKIP_DIR_NAMES:
                # rglob не умеет prune, но пропускаем содержимое через проверку частей.
                continue
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() not in extensions:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield path


def score_file(path: Path, terms: list[Term], focus=None) -> Hit | None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    lower = text.lower()
    path_lower = str(path).lower()
    score = 0
    matched: list[tuple[int, str]] = []
    best_term: Term | None = None

    for term in terms:
        count = lower.count(term.text)
        path_bonus = 0
        if term.text in path_lower:
            path_bonus = 8 * term.weight
        if count == 0 and path_bonus == 0:
            continue
        capped = min(count, MAX_OCCURRENCES_PER_TERM)
        term_score = capped * term.weight + path_bonus
        score += term_score
        matched.append((term_score, term.text))
        if best_term is None or term.weight > best_term.weight:
            best_term = term

    if score == 0:
        return None
    if focus is not None:
        score += path_score_bonus(path, focus)

    matched.sort(reverse=True)
    term_hits = [t for _, t in matched[:6]]
    snippet = _first_snippet(text, best_term.text if best_term else term_hits[0])
    return Hit(path, score, term_hits, snippet)


def _first_snippet(text: str, term: str) -> str:
    for line in text.splitlines():
        if term in line.lower():
            clean = line.strip()
            if len(clean) > 160:
                clean = clean[:157] + "..."
            return clean
    return ""


def search_area(kb_root: Path, roots: list[str], extensions: set[str],
                terms: list[Term], limit: int, focus=None) -> list[Hit]:
    hits: list[Hit] = []
    for rel in roots:
        for path in _iter_files(kb_root / rel, extensions):
            hit = score_file(path, terms, focus)
            if hit:
                hits.append(hit)
    hits.sort(key=lambda h: (-h.score, str(h.path)))
    return hits[:limit]


# --------------------------------------------------------------------------- #
# Сборка discovery-пакета
# --------------------------------------------------------------------------- #

def _rel(path: Path, kb_root: Path) -> str:
    try:
        return str(path.relative_to(kb_root))
    except ValueError:
        return str(path)


def _hit_rows(hits: list[Hit], kb_root: Path) -> list[str]:
    rows = []
    for hit in hits:
        terms = ", ".join(f"`{t}`" for t in hit.term_hits) or "—"
        snippet = hit.snippet.replace("|", "\\|") if hit.snippet else "—"
        rows.append(
            f"| `{_rel(hit.path, kb_root)}` | {hit.score} | {terms} | {snippet} |"
        )
    return rows


def build_package(kb_root: Path, brief: str, *, name: str, terms_extra: str | None,
                  doc_limit: int, code_limit: int) -> str:
    focus = detect_focus(brief)
    terms = extract_terms(brief, terms_extra)
    if not terms:
        return "Ошибка: не удалось выделить поисковые термины из брифа."

    docs = search_area(kb_root, DOC_ROOTS, DOC_EXTENSIONS, terms, doc_limit, focus)
    analytics = search_area(kb_root, [ANALYTICS_ROOT], ANALYTICS_EXTENSIONS,
                            terms, doc_limit, focus)
    code = search_area(kb_root, [CODE_ROOT], CODE_EXTENSIONS, terms, code_limit, focus)
    data = search_area(kb_root, [DATA_ROOT], DATA_EXTENSIONS, terms, code_limit, focus)
    aux = search_area(kb_root, [AUX_ROOT], CODE_EXTENSIONS | DATA_EXTENSIONS,
                      terms, code_limit, focus)

    term_line = ", ".join(f"`{t.text}`(×{t.weight})" for t in terms[:25])

    def section(title: str, hits: list[Hit], empty: str) -> list[str]:
        block = [f"### {title}", ""]
        if not hits:
            block.extend([empty, ""])
            return block
        block.extend([
            "| Файл | Score | Совпавшие термины | Фрагмент |",
            "|---|---|---|---|",
            *_hit_rows(hits, kb_root),
            "",
        ])
        return block

    parts = [
        "# INTERNAL: discovery-пакет контекста фичи (не отдавать как есть)",
        "",
        "## Бриф",
        brief.strip(),
        "",
        "## Поисковые термины (вес = приоритет)",
        term_line,
        "",
        f"Области поиска: аналитика `analytics/`, спецификации `{FEATURE_WRITING_DIR}/`, "
        "код `repositories/`, данные `db-export/`, доп. материалы `auxiliary/`.",
        "",
        "## Кандидаты (ранжированы по score)",
        "",
        *focus_instruction_lines(focus),
        *section(f"Спецификации фич ({FEATURE_WRITING_DIR}/)", docs,
                 f"Совпадений в {FEATURE_WRITING_DIR}/ не найдено."),
        *section("Аналитика (analytics/)", analytics,
                 "Совпадений в analytics/ не найдено."),
        *section("Код и контракты (repositories/)", code,
                 "Совпадений в репозиториях не найдено."),
        *section("Данные (db-export/)", data,
                 "Совпадений в выгрузках БД не найдено."),
        *section("Доп. материалы (auxiliary/)", aux,
                 "Совпадений в auxiliary не найдено."),
        "## Инструкция для агента",
        "1. Сначала открой файлы из § «Фокус поиска», затем топ по score. "
        "При необходимости расширь поиск Grep по тем же терминам и якорям фокуса.",
        "2. Не подтверждай факты по одному имени файла — открой файл и проверь "
        "содержимое (класс, метод, endpoint, proto-сообщение, таблицу, поле).",
        "3. `analytics/` — актуальная аналитика и выгрузка Confluence по "
        "фичам: используй для бизнес-контекста, AS IS / TO BE, требований. "
        "Технические факты (контракты, поля, код) подтверждай по `repositories/` "
        "и `db-export/`.",
        "4. Заполни **Скелет документа-контекста** ниже: для каждого факта дай "
        "ссылку на конкретный файл (и якорь: класс/метод/таблица/endpoint).",
        "5. Неизвестное и непроверенное помечай в разделе «Открытые вопросы», "
        "не выдумывай поведение.",
        "6. Это контекст для будущего написания фичи, а не сама "
        "фича: не проектируй решение, опиши то, что уже есть и что нужно учесть.",
        "7. В финальном документе не оставляй «INTERNAL», score-таблиц и этой "
        "инструкции.",
        "",
        "## Скелет документа-контекста (заполни и верни)",
        "",
        _context_skeleton(name, brief),
        "",
    ]
    return "\n".join(parts)


def _context_skeleton(name: str, brief: str) -> str:
    return "\n".join([
        f"# Контекст для фичи: {name}",
        "",
        "## Задача (бриф)",
        "",
        "> Кратко перескажи бриф своими словами: что меняем и зачем.",
        "",
        "## Затронутые области",
        "",
        "| Область | Что затрагивается | Документы / код |",
        "|---|---|---|",
        "| | | |",
        "",
        "## Релевантная аналитика и спеки",
        "",
        f"| Документ (analytics/, {FEATURE_WRITING_DIR}/) | Что описывает | Почему релевантно задаче |",
        "|---|---|---|",
        "| | | |",
        "",
        "## Релевантный код",
        "",
        "| Файл | Компонент (класс / метод / endpoint / proto) | Текущее поведение | Почему важно для фичи |",
        "|---|---|---|---|",
        "| | | | |",
        "",
        "## Данные (БД, выгрузки)",
        "",
        "| Таблица / поле / запрос | Где найдено | Текущее устройство | На что влияет фича |",
        "|---|---|---|---|",
        "| | | | |",
        "",
        "## Интеграции и контракты, которые нужно учесть",
        "",
        "- ",
        "",
        "## Ограничения и риски текущего состояния",
        "",
        "- ",
        "",
        "## Что учесть при написании фичи",
        "",
        "- ",
        "",
        "## Открытые вопросы / что проверить",
        "",
        "| ID | Вопрос | Где искать ответ |",
        "|---|---|---|",
        "| Q-01 | | |",
    ])


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _read_brief(args: argparse.Namespace) -> str:
    if args.brief:
        return args.brief
    if args.brief_opt:
        return args.brief_opt
    if args.brief_file:
        return Path(args.brief_file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def _slugify(text: str) -> str:
    words = re.findall(r"[a-zа-яё0-9]+", text.lower())
    return "-".join(words[:6]) or "feature"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="find-context",
        description=(
            "Ищет релевантную аналитику, спеки, код (repositories/) и db-export по брифу фичи."
        ),
    )
    parser.add_argument("brief", nargs="?", help="Бриф/задача (текст).")
    parser.add_argument("--brief", dest="brief_opt", help="Бриф (альтернатива позиционному).")
    parser.add_argument("--brief-file", help="Файл с брифом.")
    parser.add_argument("--name", help="Имя/slug фичи для заголовка контекста.")
    parser.add_argument("--terms", help="Доп. поисковые термины через пробел/запятую.")
    parser.add_argument("--doc-limit", type=int, default=15, help="Максимум документов в выдаче.")
    parser.add_argument("--code-limit", type=int, default=25, help="Максимум файлов кода/данных в выдаче.")
    parser.add_argument("--kb-root", default=".", help="Корень базы знаний. По умолчанию текущая папка.")
    parser.add_argument("--out", help="Куда записать пакет. По умолчанию stdout.")

    args = parser.parse_args(argv)
    brief = _read_brief(args).strip()
    if not brief:
        parser.error("не задан бриф: передай текст аргументом, через --brief-file или stdin.")

    kb_root = Path(args.kb_root).resolve()
    name = args.name or _slugify(brief)

    package = build_package(
        kb_root, brief,
        name=name, terms_extra=args.terms,
        doc_limit=args.doc_limit, code_limit=args.code_limit,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(package, encoding="utf-8")
        print(f"Записано: {out_path}", file=sys.stderr)
    else:
        print(package)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
