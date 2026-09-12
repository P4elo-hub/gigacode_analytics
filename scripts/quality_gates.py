#!/usr/bin/env python3
"""Исполняемые structural quality gates для SPEC (не форма kit)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from artifact_paths import resolve_slug, spec_path, workspace_root

SERVICE_MARKERS = ("INTERNAL", "> **Kit", "> **Skill", "> **Покрывает стандарты")
FORBIDDEN_USECASE_SUFFIXES = (
    "Wrapper",
    "Converter",
    "Mapper",
    "Factory",
    "Dto",
    "DTO",
)
CONTRACT_FIELD_HEADER = re.compile(
    r"\|\s*(Поле|Параметр|Атрибут|Field)\s*\|",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^#{2,4}\s+(.+)$", re.MULTILINE)
PROTOCOL_GRPC = "grpc"
PROTOCOL_REST = "rest"
PROTOCOL_ASYNC = "async"
GRPC_HINTS = ("grpc", ".proto", "protobuf")
REST_HINTS = ("openapi", "/api/", "request headers", "http method")
ASYNC_HINTS = ("kafka", "топик", "async", "асинхрон")
GRPC_MARKERS = ("rpc", "message", "metadata")
USECASE_AS_IS = re.compile(
    r"^#{2,3}\s+.*AS IS.*$(.*?)(?=^#{2,3}\s+|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)
USECASE_TO_BE = re.compile(
    r"^#{2,3}\s+.*TO BE.*$(.*?)(?=^#{2,3}\s+|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)
INTERNAL_CLASS_RE = re.compile(
    r"\b[A-Z][A-Za-z0-9]*(?:Wrapper|Converter|Mapper|Factory|Dto|DTO)\b"
)
BR_RE = re.compile(r"\bBR-\d+\b")
CN_RE = re.compile(r"\bCN-\d+\b")
GAP_TABLE_HEADER = "Gaps и допущения"
SEVERITY_FAIL = "fail"
SEVERITY_WARN = "warn"


@dataclass
class GateFinding:
    check_id: str
    severity: str
    message: str


def _has_heading_title(text: str, needle: str) -> bool:
    return any(needle.lower() in heading.lower() for heading in HEADING_RE.findall(text))


def _has_section_number(text: str, section_id: str) -> bool:
    """Точный номер раздела: `### 1.1.` да, `#### 4.1.1` для `1.1` — нет."""
    pattern = re.compile(
        rf"^#{{2,4}}\s+{re.escape(section_id)}(?:\.\s|\s|$)",
        re.MULTILINE,
    )
    return pattern.search(text) is not None


def detect_contract_protocol(spec_text: str) -> str | None:
    lower = spec_text.lower()
    if any(hint in lower for hint in GRPC_HINTS):
        return PROTOCOL_GRPC
    if any(hint in lower for hint in ASYNC_HINTS):
        return PROTOCOL_ASYNC
    if any(hint in lower for hint in REST_HINTS):
        return PROTOCOL_REST
    return None


def check_service_markers(spec_text: str) -> list[GateFinding]:
    findings: list[GateFinding] = []
    for line_number, line in enumerate(spec_text.splitlines(), start=1):
        if any(marker in line for marker in SERVICE_MARKERS):
            findings.append(
                GateFinding(
                    "QG-SERVICE-01",
                    SEVERITY_FAIL,
                    f"служебная строка kit/INTERNAL на строке {line_number}",
                )
            )
    return findings


def check_traceability(spec_text: str) -> list[GateFinding]:
    findings: list[GateFinding] = []
    if _has_section_number(spec_text, "1.1") and not BR_RE.search(spec_text):
        findings.append(GateFinding("QG-BR-01", SEVERITY_FAIL, "в документе с §1.1 нет BR-XX"))
    if _has_heading_title(spec_text, "Ограничения") and not CN_RE.search(spec_text):
        findings.append(GateFinding("QG-CN-01", SEVERITY_WARN, "в §2 нет CN-XX"))
    return findings


def check_usecase_internals(spec_text: str) -> list[GateFinding]:
    findings: list[GateFinding] = []
    for heading, pattern in (("AS IS", USECASE_AS_IS), ("TO BE", USECASE_TO_BE)):
        for match in pattern.finditer(spec_text):
            internals = sorted(set(INTERNAL_CLASS_RE.findall(match.group(1))))
            if internals:
                findings.append(
                    GateFinding(
                        "QG-UC-01",
                        SEVERITY_FAIL,
                        f"внутренние классы в Use Case {heading}: " + ", ".join(internals),
                    )
                )
    return findings


def check_contracts(spec_text: str, protocol: str | None = None) -> list[GateFinding]:
    findings: list[GateFinding] = []
    has_contract_section = (
        _has_section_number(spec_text, "4.1.1") or "контракт" in spec_text.lower()
    )
    if not has_contract_section:
        return findings
    if not CONTRACT_FIELD_HEADER.search(spec_text):
        findings.append(
            GateFinding(
                "QG-CONTRACT-01",
                SEVERITY_FAIL,
                "есть интеграционный раздел, но нет таблицы полей (| Поле | / | Параметр |)",
            )
        )
    resolved_protocol = (protocol or detect_contract_protocol(spec_text) or "").lower()
    if resolved_protocol == PROTOCOL_GRPC:
        missing_markers = [
            marker
            for marker in GRPC_MARKERS
            if not re.search(rf"\b{re.escape(marker)}\b", spec_text, re.IGNORECASE)
        ]
        if missing_markers:
            findings.append(
                GateFinding(
                    "QG-CONTRACT-02",
                    SEVERITY_WARN,
                    "для gRPC в spec нет маркеров: " + ", ".join(missing_markers),
                )
            )
    return findings


def check_gaps_table(spec_text: str) -> list[GateFinding]:
    if "[GAP-" not in spec_text:
        return []
    if GAP_TABLE_HEADER.lower() in spec_text.lower():
        return []
    return [
        GateFinding(
            "QG-GAP-01",
            SEVERITY_WARN,
            "есть inline [GAP-...], но нет таблицы «Gaps и допущения»",
        )
    ]


def run_gates(spec_text: str, protocol: str | None = None) -> list[GateFinding]:
    findings: list[GateFinding] = []
    findings.extend(check_service_markers(spec_text))
    findings.extend(check_traceability(spec_text))
    findings.extend(check_usecase_internals(spec_text))
    findings.extend(check_contracts(spec_text, protocol))
    findings.extend(check_gaps_table(spec_text))
    return findings


def render_markdown(slug: str, findings: list[GateFinding]) -> str:
    fails = [item for item in findings if item.severity == SEVERITY_FAIL]
    warns = [item for item in findings if item.severity == SEVERITY_WARN]
    verdict = "FAIL" if fails else "PASS"
    lines = [
        f"## Quality gates: {slug}",
        "",
        f"**Вердикт:** {verdict} · fail: {len(fails)} · warn: {len(warns)}",
        "",
    ]
    if not findings:
        lines.append("Нарушений формы нет.")
        return "\n".join(lines) + "\n"
    lines.extend(["| ID | Severity | Сообщение |", "|----|----------|-----------|"])
    for item in findings:
        lines.append(f"| {item.check_id} | {item.severity} | {item.message} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quality-gates")
    parser.add_argument("target", help="slug фичи или путь к SPEC")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--protocol", help="Протокол контракта: REST, gRPC, Async.")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = workspace_root(Path(args.root))
    slug = resolve_slug(args.target, root) or args.target
    spec = Path(args.target)
    if not spec.is_file():
        spec = spec_path(root, slug)
    if not spec.is_file():
        print(f"SPEC не найден: {spec}", file=sys.stderr)
        return 1
    findings = run_gates(spec.read_text(encoding="utf-8"), args.protocol)
    if args.json:
        print(json.dumps([asdict(item) for item in findings], ensure_ascii=False, indent=2))
    else:
        print(render_markdown(slug, findings), end="")
    return 1 if any(item.severity == SEVERITY_FAIL for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
