# ==============================================================================================================================
#      File     : scripts/build_template.py
#      Project  : MZCMST AI Migration PoC
#      Description: ASL JSON 을 읽어 CFN template 의 PipelineStateMachine.DefinitionString 으로 주입한 빌드 산출물 생성
#      Author   : Joseph Kim <josephkim@mz.co.kr>
#      Date     : 2026-05-11
#      Branch   : feature/ai-mig-poc-infra
#      Usage    : python3 scripts/build_template.py <template_src> <asl_src> <template_out>
#      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
#
#      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
#      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
# ==============================================================================================================================
"""
PipelineStateMachine 의 DefinitionString 블록(placeholder JSON)을
infra/statemachine/pipeline.asl.json 의 실제 ASL 로 교체한다.

YAML block scalar 종료 규칙(같거나 짧은 들여쓰기 비공백 라인에서 종료)을
라인 단위로 직접 적용하여, 뒤따르는 sibling key(Tags 등) 가 흡수되는 사고를 방지한다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


HEADER_PREFIX = "DefinitionString:"


def leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def find_header_line(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        stripped = line.lstrip(" ")
        if stripped.startswith(HEADER_PREFIX):
            return i
    raise SystemExit("error: DefinitionString header not found in template")


def find_body_end(lines: list[str], header_idx: int, header_indent: int) -> int:
    """헤더 다음 라인부터 본문 끝(exclusive) 인덱스 반환.
    빈 라인은 본문에 포함, header_indent 이하의 비공백 라인이 나오면 종료.
    """
    n = len(lines)
    end = header_idx + 1
    while end < n:
        line = lines[end]
        if line.strip() == "":
            end += 1
            continue
        if leading_spaces(line) > header_indent:
            end += 1
            continue
        break
    return end


def build_replacement(asl_obj: dict, header_line: str, header_indent: int) -> list[str]:
    """헤더 라인 + indented ASL 본문 라인들."""
    body_indent = " " * (header_indent + 2)
    asl_pretty = json.dumps(asl_obj, indent=2, ensure_ascii=False)
    body_lines = [body_indent + ln + "\n" for ln in asl_pretty.splitlines()]
    return [header_line] + body_lines


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: build_template.py <template_src> <asl_src> <template_out>", file=sys.stderr)
        return 2

    template_src = Path(argv[1])
    asl_src = Path(argv[2])
    template_out = Path(argv[3])

    text = template_src.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    header_idx = find_header_line(lines)
    header_line = lines[header_idx]
    header_indent = leading_spaces(header_line)

    if not header_line.rstrip().endswith("|"):
        print(f"error: DefinitionString must use block scalar '|'. got: {header_line.rstrip()}", file=sys.stderr)
        return 1

    body_end = find_body_end(lines, header_idx, header_indent)
    asl_obj = json.loads(asl_src.read_text(encoding="utf-8"))
    replacement = build_replacement(asl_obj, header_line, header_indent)

    new_lines = lines[:header_idx] + replacement + lines[body_end:]
    template_out.parent.mkdir(parents=True, exist_ok=True)
    template_out.write_text("".join(new_lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
