#!/usr/bin/env python3
"""pitest 의 mutations.xml 을 읽어 '메워야 할 구멍' 목록을 JSON 으로 뽑는다.

이 스크립트의 출력이 곧 에이전트의 입력이다. 그래서 하는 일을 둘로 좁혔다 — 파싱과 집계.
어느 뮤턴트를 먼저 칠지 고르는 것도, 전/후를 비교해 킬을 판정하는 것도 여기서 하지 않는다.
그건 상태를 들고 있어야 하는 일이고, 이 스크립트는 같은 입력에 항상 같은 출력을 낸다.

사용:
    python3 parse_mutations.py [리포트경로] [-o 출력파일]
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# pitest 가 뱉는 상태값 분류.
# 지금 이 프로젝트에는 KILLED / SURVIVED / NO_COVERAGE 셋뿐이지만 나머지도 미리 적어둔다 —
# 남의 프로젝트에 이식했을 때(S6) 처음 보는 상태를 만나는 것은 시간 문제다.
KILLED_STATUSES = frozenset({"KILLED", "TIMED_OUT", "MEMORY_ERROR"})
SURVIVING_STATUSES = frozenset({"SURVIVED", "NO_COVERAGE"})
EXCLUDED_STATUSES = frozenset({"RUN_ERROR", "NON_VIABLE"})

DEFAULT_REPORT = "build/reports/pitest/mutations.xml"


class MutationReportError(Exception):
    """리포트가 우리가 아는 모양이 아닐 때 던진다.

    채점 기계가 조용히 틀리면 이 프로젝트 전체가 무의미해진다.
    애매한 입력은 넘기지 말고 여기서 멈춘다.
    """


def classify(status):
    """상태값을 killed / gap / excluded 셋 중 하나로 접는다."""
    if status in KILLED_STATUSES:
        return "killed"
    if status in SURVIVING_STATUSES:
        return "gap"
    if status in EXCLUDED_STATUSES:
        # 뮤턴트 자체가 실행 불가능했던 경우. 성과도 목표도 아니라 분모에서 뺀다.
        return "excluded"
    raise MutationReportError(
        f"모르는 뮤턴트 상태다: {status!r}. "
        "조용히 무시하면 집계가 틀어진 채로 굴러간다 — 분류에 추가하고 다시 돌린다."
    )


def short_mutator(full_name):
    """org.pitest...mutators.NegateConditionalsMutator → NegateConditionals 로 줄인다.

    'Mutator' 를 한 번만 지우는 이유는 RemoveConditionalMutator_EQUAL_ELSE 처럼
    이름 가운데에 끼어 있는 경우가 있어서다 → RemoveConditional_EQUAL_ELSE.
    """
    simple = full_name.rsplit(".", 1)[-1]
    return simple.replace("Mutator", "", 1)


def _require_text(node, tag):
    child = node.find(tag)
    if child is None or child.text is None or not child.text.strip():
        raise MutationReportError(f"<mutation> 에 <{tag}> 가 없다: {ET.tostring(node)[:200]!r}")
    return child.text.strip()


def _read_mutation(node, short_name_origins):
    """<mutation> 하나를 딕셔너리로 옮긴다."""
    status = node.get("status")
    if not status:
        raise MutationReportError("status 속성이 없는 <mutation> 이 있다")

    full_mutator = _require_text(node, "mutator")
    mutator = short_mutator(full_mutator)

    # 축약이 서로 다른 뮤테이터를 같은 이름으로 뭉갠다면 id 가 겹친다.
    # 실제로 겹친 적은 없지만, 겹치는 순간 조용히 뮤턴트를 잃으므로 지켜본다.
    origin = short_name_origins.setdefault(mutator, full_mutator)
    if origin != full_mutator:
        raise MutationReportError(
            f"서로 다른 뮤테이터가 같은 축약 이름을 갖는다: {mutator!r} "
            f"← {origin!r} / {full_mutator!r}"
        )

    # indexes 는 한 줄에 같은 뮤테이터가 여러 번 적용될 때 그 지점을 가르는 유일한 값이다.
    # 없는 리포트가 있더라도 여기서 막지는 않는다 — 진짜 문제(id 충돌)는 parse_report 가 잡는다.
    indexes = [int(index.text) for index in node.findall("indexes/index")]

    mutated_class = _require_text(node, "mutatedClass")
    method = _require_text(node, "mutatedMethod")
    line = int(_require_text(node, "lineNumber"))

    return {
        "id": build_id(mutated_class, method, line, mutator, indexes),
        "class": mutated_class,
        "source_file": _require_text(node, "sourceFile"),
        "method": method,
        "line": line,
        "mutator": mutator,
        "indexes": indexes,
        "status": status,
        "description": _require_text(node, "description"),
        "tests_run": int(node.get("numberOfTestsRun", "0")),
    }


def build_id(mutated_class, method, line, mutator, indexes):
    """안정 식별자: 클래스#메서드:라인:뮤테이터:인덱스

    indexes 를 빼면 한 줄에 조건이 둘일 때(`member && grade == VIP`) id 가 겹친다.
    겹친 id 하나를 '포기'로 기록하는 순간 죽일 수 있는 나머지도 목표에서 함께 빠진다.
    """
    joined = "-".join(str(index) for index in indexes)
    return f"{mutated_class}#{method}:{line}:{mutator}:{joined}"


def parse_report(path):
    """mutations.xml 을 읽어 {report, summary, survivors} 를 돌려준다."""
    path = Path(path)
    if not path.is_file():
        raise MutationReportError(f"리포트가 없다: {path} — 먼저 ./gradlew pitest 를 돌린다")

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        raise MutationReportError(f"XML 을 읽을 수 없다: {path} ({error})") from error

    counts = {}
    survivors = []
    short_name_origins = {}
    seen_ids = set()
    total = killed = excluded = 0

    for node in root.findall("mutation"):
        mutant = _read_mutation(node, short_name_origins)
        total += 1

        if mutant["id"] in seen_ids:
            raise MutationReportError(
                f"뮤턴트 id 가 겹친다: {mutant['id']} — "
                "식별자가 유일하지 않으면 하나를 포기할 때 나머지도 함께 사라진다."
            )
        seen_ids.add(mutant["id"])

        counts[mutant["status"]] = counts.get(mutant["status"], 0) + 1

        bucket = classify(mutant["status"])
        if bucket == "killed":
            killed += 1
        elif bucket == "excluded":
            excluded += 1
        else:
            survivors.append(mutant)

    # 출력이 매번 같은 순서여야 diff 가 감사 로그 역할을 한다.
    survivors.sort(key=lambda m: (m["class"], m["line"], m["mutator"], m["indexes"]))

    scored = total - excluded
    return {
        "report": str(path),
        "summary": {
            "total": total,
            "killed": killed,
            "survived": counts.get("SURVIVED", 0),
            "no_coverage": counts.get("NO_COVERAGE", 0),
            "excluded": excluded,
            "gaps": len(survivors),
            "mutation_score": round(100 * killed / scored, 2) if scored else 0.0,
            "by_status": dict(sorted(counts.items())),
        },
        "survivors": survivors,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="pitest mutations.xml → 생존 뮤턴트 JSON")
    parser.add_argument(
        "report",
        nargs="?",
        default=DEFAULT_REPORT,
        help=f"mutations.xml 경로 (기본: {DEFAULT_REPORT})",
    )
    parser.add_argument("-o", "--output", help="결과를 쓸 파일 (기본: 표준 출력)")
    args = parser.parse_args(argv)

    try:
        result = parse_report(args.report)
    except MutationReportError as error:
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
