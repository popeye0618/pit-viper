#!/usr/bin/env python3
"""Jacoco 의 jacocoTestReport.xml 을 읽어 '테스트가 닿지 않은 자리'를 JSON 으로 뽑는다.

퍼널의 앞단이다. pitest 는 분 단위지만 이쪽은 초 단위라, 큰 구멍을 먼저 이걸로 메우면
비싼 신호를 돌리는 횟수가 줄어든다.

parse_mutations.py 와 같은 계약을 지킨다 — 파싱과 집계만 하고, 고르거나 판정하지 않는다.

사용:
    python3 parse_jacoco.py [리포트경로] [-o 출력파일]
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_REPORT = "build/reports/jacoco/test/jacocoTestReport.xml"


class CoverageReportError(Exception):
    """리포트가 우리가 아는 모양이 아닐 때 던진다."""


def _counter(node, counter_type):
    """<counter type="LINE" missed="58" covered="59"/> → {covered, missed, total, percent}

    해당 counter 가 없으면 0 으로 둔다. 분기가 하나도 없는 클래스에는 BRANCH counter 가
    아예 없는 것이 정상이라, 여기서는 없는 것을 이상 신호로 보지 않는다.
    """
    found = node.find(f"counter[@type='{counter_type}']")
    if found is None:
        return {"covered": 0, "missed": 0, "total": 0, "percent": 0.0}

    covered = int(found.get("covered", "0"))
    missed = int(found.get("missed", "0"))
    total = covered + missed
    return {
        "covered": covered,
        "missed": missed,
        "total": total,
        "percent": round(100 * covered / total, 2) if total else 0.0,
    }


def _line_status(line):
    """<line nr="15" mi="0" ci="12" mb="0" cb="0"/> 한 줄을 읽는다.

    mi/ci = missed/covered instructions, mb/cb = missed/covered branches.
    ci 가 0 이면 그 줄은 한 번도 실행되지 않았다.

    속성 이름이 바뀌면 .get() 이 None 을 돌려주고 모든 줄이 '커버됨'으로 분류되면서
    구멍이 통째로 사라진다. 조용히 틀리는 경로라 여기서 막는다.
    """
    number = line.get("nr")
    missed_instructions = line.get("mi")
    covered_instructions = line.get("ci")
    if number is None or missed_instructions is None or covered_instructions is None:
        raise CoverageReportError(
            f"<line> 에 nr/mi/ci 가 없다: {line.attrib} — Jacoco 리포트 형식이 바뀌었는지 확인한다"
        )

    return {
        "number": int(number),
        "covered_instructions": int(covered_instructions),
        "missed_branches": int(line.get("mb", "0")),
        "covered_branches": int(line.get("cb", "0")),
    }


def _read_source_file(package_name, source_file):
    """<sourcefile> 하나를 구멍 목록으로 옮긴다.

    라인 번호는 클래스가 아니라 소스 파일에 달려 있다. 그래서 집계 단위도 파일이다 —
    한 파일에 중첩 클래스가 여럿이면 그 줄들이 여기 함께 담긴다. 어차피 에이전트가
    열어서 고칠 대상은 '파일'이므로 이 단위가 맞다.
    """
    file_name = source_file.get("name")
    if not file_name:
        raise CoverageReportError(f"<sourcefile> 에 name 이 없다: {package_name}")

    uncovered = []
    partial = []
    for line in source_file.findall("line"):
        parsed = _line_status(line)
        if parsed["covered_instructions"] == 0:
            # 아무 테스트도 이 줄을 실행하지 않았다.
            uncovered.append(parsed["number"])
        elif parsed["missed_branches"] > 0:
            # 줄은 실행됐는데 안 가본 분기가 남았다 — pitest 가 생존 뮤턴트로 잡을 자리와 겹친다.
            partial.append({
                "line": parsed["number"],
                "covered_branches": parsed["covered_branches"],
                "missed_branches": parsed["missed_branches"],
            })

    return {
        "class": f"{package_name}.{file_name.removesuffix('.java')}".replace("/", "."),
        "source_file": file_name,
        "path": f"{package_name}/{file_name}",
        "line": _counter(source_file, "LINE"),
        "branch": _counter(source_file, "BRANCH"),
        "uncovered_lines": uncovered,
        "partial_lines": partial,
    }


def parse_report(path):
    """jacocoTestReport.xml 을 읽어 {report, summary, gaps} 를 돌려준다."""
    path = Path(path)
    if not path.is_file():
        raise CoverageReportError(
            f"리포트가 없다: {path} — 먼저 ./gradlew test jacocoTestReport 를 돌린다"
        )

    try:
        # Jacoco XML 은 DTD 를 참조한다. 파서가 외부 DTD 를 받으러 나가지 않도록 그냥 무시된다.
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        raise CoverageReportError(f"XML 을 읽을 수 없다: {path} ({error})") from error

    gaps = []
    for package in root.findall("package"):
        package_name = package.get("name")
        if package_name is None:
            raise CoverageReportError("<package> 에 name 이 없다")

        for source_file in package.findall("sourcefile"):
            entry = _read_source_file(package_name, source_file)
            # 빈틈이 없는 파일은 목표가 아니다. 전체 집계는 아래 summary 가 따로 들고 있다.
            if entry["uncovered_lines"] or entry["partial_lines"]:
                gaps.append(entry)

    # 출력이 매번 같은 순서여야 diff 가 감사 로그 역할을 한다.
    gaps.sort(key=lambda g: g["class"])

    return {
        "report": str(path),
        "summary": {
            "line": _counter(root, "LINE"),
            "branch": _counter(root, "BRANCH"),
            "gap_files": len(gaps),
            "uncovered_lines": sum(len(g["uncovered_lines"]) for g in gaps),
            "partial_lines": sum(len(g["partial_lines"]) for g in gaps),
        },
        "gaps": gaps,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Jacoco XML → 미커버 라인 JSON")
    parser.add_argument(
        "report",
        nargs="?",
        default=DEFAULT_REPORT,
        help=f"jacocoTestReport.xml 경로 (기본: {DEFAULT_REPORT})",
    )
    parser.add_argument("-o", "--output", help="결과를 쓸 파일 (기본: 표준 출력)")
    args = parser.parse_args(argv)

    try:
        result = parse_report(args.report)
    except CoverageReportError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
