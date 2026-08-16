#!/usr/bin/env python3
"""루프가 끝난 뒤 사람이 읽을 리포트를 조립한다.

에이전트가 성과를 서술하지 않는다. 리포트의 모든 숫자와 목록은
`state.json`(스크립트가 쓴 것)과 전/후 리포트에서만 나온다 — 원칙 1·2.

사용:
    report.py --before <전> --after <후> [--state 경로] [-o 파일]
"""

import argparse
import json
import sys
from pathlib import Path

import parse_mutations
import verdict

# 리포트에 싣는 순서. 성과 → 사유 있는 포기 → 사유 없는 포기 → 남은 것.
SECTIONS = [
    (verdict.KILLED, "죽인 뮤턴트"),
    (verdict.EQUIVALENT, "동등 뮤턴트로 닫은 것"),
    (verdict.EXHAUSTED, "예산을 소진해 포기한 것"),
    (verdict.SURVIVING, "아직 남은 목표"),
    (verdict.GONE, "리포트에서 사라진 것"),
]


def _row(mutant_id, entry, catalog):
    """id 로 뮤턴트 좌표를 찾아 표 한 줄을 만든다."""
    mutant = catalog.get(mutant_id)
    if mutant is None:
        # 전/후 어디에도 없는 id. state 만 남은 경우라 id 를 그대로 보여준다.
        return f"| `{mutant_id}` | | | {entry['attempts']} |"
    where = f"{mutant['class'].rsplit('.', 1)[-1]}#{mutant['method']}:{mutant['line']}"
    return (f"| {where} | {mutant['mutator']} | {mutant['description']} | {entry['attempts']} |")


def build(before_path, after_path, state):
    before = parse_mutations.parse_report(before_path, include_all=True)
    after = parse_mutations.parse_report(after_path, include_all=True)

    # 좌표 사전. 후 리포트를 우선하되, 사라진 뮤턴트는 전 리포트에서 찾는다.
    catalog = {m["id"]: m for m in before["all"]}
    catalog.update({m["id"]: m for m in after["all"]})

    grouped = {outcome: [] for outcome, _ in SECTIONS}
    for mutant_id, entry in sorted(state["mutants"].items()):
        grouped.setdefault(entry["outcome"], []).append((mutant_id, entry))

    b, a = before["summary"], after["summary"]
    lines = [
        "# pit-viper 리포트",
        "",
        f"회전 {state['run']}회 · 뮤턴트당 시도 예산 {state['budget']}회",
        "",
        "## 요약",
        "",
        "| 지표 | 전 | 후 |",
        "|---|---|---|",
        f"| 뮤테이션 스코어 | {b['mutation_score']}% | **{a['mutation_score']}%** |",
        f"| 잡힌 뮤턴트 | {b['killed']}/{b['total']} | **{a['killed']}/{a['total']}** |",
        f"| 구멍 (생존 + 무커버) | {b['gaps']} | **{a['gaps']}** |",
        "",
    ]

    killed = len(grouped.get(verdict.KILLED, []))
    if b["gaps"]:
        lines += [f"기준선의 구멍 {b['gaps']}개 중 **{killed}개를 죽였다** "
                  f"({round(100 * killed / b['gaps'])}%).", ""]

    for outcome, title in SECTIONS:
        rows = grouped.get(outcome, [])
        if not rows:
            continue
        lines += [f"## {title} ({len(rows)})", ""]

        if outcome == verdict.EQUIVALENT:
            # 사유가 본문이다. 사유 없이 닫힌 것이 없다는 것을 눈으로 확인할 수 있어야 한다.
            lines += ["| 위치 | 뮤테이터 | 사유 |", "|---|---|---|"]
            for mutant_id, entry in rows:
                mutant = catalog.get(mutant_id, {})
                where = (f"{mutant['class'].rsplit('.', 1)[-1]}#{mutant['method']}:{mutant['line']}"
                         if mutant else mutant_id)
                lines.append(f"| {where} | {mutant.get('mutator', '')} | {entry.get('reason', '')} |")
        else:
            lines += ["| 위치 | 뮤테이터 | 변형 | 시도 |", "|---|---|---|---|"]
            lines += [_row(mutant_id, entry, catalog) for mutant_id, entry in rows]
        lines.append("")

    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="루프 결과 마크다운 리포트")
    parser.add_argument("--before", required=True, help="루프 시작 시점의 mutations.xml")
    parser.add_argument("--after", default=parse_mutations.DEFAULT_REPORT, help="현재 mutations.xml")
    parser.add_argument("--state", default=verdict.DEFAULT_STATE, help="상태 파일")
    parser.add_argument("-o", "--output", help="쓸 파일 (기본: 표준 출력)")
    args = parser.parse_args(argv)

    try:
        state = verdict.load_state(args.state)
        text = build(args.before, args.after, state)
    except (verdict.VerdictError, parse_mutations.MutationReportError) as error:
        print(f"error: {error}", file=sys.stderr)
        return verdict.EXIT_ERROR

    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
