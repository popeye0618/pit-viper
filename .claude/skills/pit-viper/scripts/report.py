#!/usr/bin/env python3
"""루프가 끝난 뒤 사람이 읽을 리포트를 조립한다.

에이전트가 성과를 서술하지 않는다. 리포트의 모든 숫자와 목록은
`state.json`(스크립트가 쓴 것)과 전/후 리포트에서만 나온다 — 원칙 1·2.

기본 출력은 프로젝트 최상위의 `viper/` 디렉터리에 시각이 박힌 파일로 쌓인다.
같은 프로젝트를 여러 번 돌린 기록이 서로 덮이지 않게 하기 위해서다.

사용:
    report.py --before <전> [--after <후>] [--scope <범위>] [--out-dir viper]
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import parse_mutations
import verdict

DEFAULT_OUT_DIR = "viper"

# 리포트에 싣는 순서. 성과 → 사유 있는 포기 → 사유 없는 포기 → 남은 것.
SECTIONS = [
    (verdict.KILLED, "죽인 뮤턴트"),
    (verdict.EQUIVALENT, "동등 뮤턴트로 닫은 것"),
    (verdict.EXHAUSTED, "예산을 소진해 포기한 것"),
    (verdict.SURVIVING, "아직 남은 목표"),
    (verdict.GONE, "리포트에서 사라진 것"),
]

# pitest 가 주는 description 은 영어인 데다 클래스 경로까지 섞여 있어 읽기 나쁘다
# ("replaced boolean return with true for com/pitviper/.../Money::isZero").
# 뮤테이터 이름만으로 "무엇을 바꿨는지"가 결정되므로 여기서 한국어로 옮긴다.
MUTATOR_KO = {
    "ConditionalsBoundary": "경계 조건을 바꿨다 (`<` ↔ `<=`, `>` ↔ `>=`)",
    "NegateConditionals": "조건을 뒤집었다",
    "RemoveConditional_EQUAL_IF": "같음 비교를 없애고 참으로 고정했다",
    "RemoveConditional_EQUAL_ELSE": "같음 비교를 없애고 거짓으로 고정했다",
    "RemoveConditional_ORDER_IF": "크기 비교를 없애고 참으로 고정했다",
    "RemoveConditional_ORDER_ELSE": "크기 비교를 없애고 거짓으로 고정했다",
    "Math": "산술 연산자를 바꿨다 (`+` ↔ `-`, `*` ↔ `/`)",
    "Increments": "증감 방향을 뒤집었다 (`++` ↔ `--`)",
    "InvertNegs": "부호를 뒤집었다",
    "PrimitiveReturns": "반환값을 0으로 바꿨다",
    "BooleanTrueReturnVals": "반환값을 항상 `true` 로 바꿨다",
    "BooleanFalseReturnVals": "반환값을 항상 `false` 로 바꿨다",
    "NullReturnVals": "반환값을 `null` 로 바꿨다",
    "EmptyObjectReturnVals": "반환값을 빈 객체로 바꿨다",
    "VoidMethodCalls": "메서드 호출을 지웠다",
    "NonVoidMethodCalls": "메서드 호출을 지우고 기본값을 썼다",
    "ConstructorCalls": "생성자 호출을 `null` 로 바꿨다",
    "ArgumentPropagation": "반환값 대신 인자를 그대로 돌려줬다",
    "RemoveIncrements": "증감을 지웠다",
}


def describe(mutant):
    """뮤테이터를 한국어로 설명한다. 모르는 유형이면 pitest 의 원문을 그대로 쓴다.

    여기서 터뜨리지 않는 이유는, 이 스크립트가 채점자가 아니라 표시 계층이기 때문이다.
    번역이 없다고 리포트를 못 내는 것보다 영어로라도 보여주는 편이 낫다.
    """
    return MUTATOR_KO.get(mutant["mutator"], mutant["description"])


def _git(*args):
    """git 정보는 있으면 좋고 없어도 그만이다. 실패하면 조용히 비운다."""
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              timeout=5, check=True).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def _where(mutant, mutant_id):
    if mutant is None:
        return f"`{mutant_id}`"
    return f"{mutant['class'].rsplit('.', 1)[-1]}#{mutant['method']}:{mutant['line']}"


def stale_after(state, after):
    """state 는 죽었다는데 후 리포트에서는 살아 있는 뮤턴트를 찾는다.

    둘이 어긋나는 경우는 사실상 하나다 — 후 리포트가 낡았다. Gradle 이 pitest 를
    UP-TO-DATE 로 건너뛰면 직전 실행의 XML 이 그대로 남는데, 그러면 요약만 조용히
    틀린 리포트가 나온다. 목록은 state 에서 오므로 아무 데도 티가 나지 않는다.
    """
    surviving_now = {m["id"] for m in after["survivors"]}
    return sorted(
        mutant_id for mutant_id, entry in state["mutants"].items()
        if entry["outcome"] == verdict.KILLED and mutant_id in surviving_now
    )


def build(before_path, after_path, state, scope=None, generated_at=None):
    before = parse_mutations.parse_report(before_path, include_all=True)
    after = parse_mutations.parse_report(after_path, include_all=True)

    # 좌표 사전. 후 리포트를 우선하되, 사라진 뮤턴트는 전 리포트에서 찾는다.
    catalog = {m["id"]: m for m in before["all"]}
    catalog.update({m["id"]: m for m in after["all"]})

    grouped = {outcome: [] for outcome, _ in SECTIONS}
    for mutant_id, entry in sorted(state["mutants"].items()):
        grouped.setdefault(entry["outcome"], []).append((mutant_id, entry))

    generated_at = generated_at or datetime.now().astimezone()
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    commit = _git("rev-parse", "--short", "HEAD")
    revision = f"{branch} ({commit})" if branch and commit else "—"

    b, a = before["summary"], after["summary"]
    lines = [
        "# pit-viper 리포트",
        "",
        "| | |",
        "|---|---|",
        f"| 생성 시각 | {generated_at:%Y-%m-%d %H:%M:%S %Z} |",
        f"| 프로젝트 | {Path.cwd().name} |",
        f"| 브랜치 | {revision} |",
        f"| 대상 범위 | {scope or '전체'} |",
        f"| 회전 | {state['run']}회 · 뮤턴트당 시도 예산 {state['budget']}회 |",
        "",
    ]

    stale = stale_after(state, after)
    if stale:
        lines += [
            f"> ⚠️ **아래 '후' 숫자를 믿지 말 것.** 죽었다고 기록된 뮤턴트 {len(stale)}개가 "
            "후 리포트에서 아직 살아 있다. pitest 리포트가 낡았을 가능성이 높다 — "
            "`./gradlew pitest --rerun-tasks` 로 다시 만든 뒤 리포트를 재생성한다.",
            "",
        ]

    lines += [
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
            lines += ["| 위치 | 무엇을 바꿨나 | 동등으로 판정한 이유 |", "|---|---|---|"]
            for mutant_id, entry in rows:
                mutant = catalog.get(mutant_id)
                change = describe(mutant) if mutant else ""
                lines.append(f"| {_where(mutant, mutant_id)} | {change} | {entry.get('reason', '')} |")
        else:
            lines += ["| 위치 | 무엇을 바꿨나 | 시도 |", "|---|---|---|"]
            for mutant_id, entry in rows:
                mutant = catalog.get(mutant_id)
                change = describe(mutant) if mutant else ""
                lines.append(f"| {_where(mutant, mutant_id)} | {change} | {entry['attempts']} |")
        lines.append("")

    return "\n".join(lines)


def output_path(out_dir, generated_at):
    """viper/pit-viper-20260816-1352.md — 같은 프로젝트의 기록이 서로 덮이지 않게 한다."""
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"pit-viper-{generated_at:%Y%m%d-%H%M%S}.md"


def main(argv=None):
    parser = argparse.ArgumentParser(description="루프 결과 마크다운 리포트")
    parser.add_argument("--before", required=True, help="루프 시작 시점의 mutations.xml")
    parser.add_argument("--after", default=parse_mutations.DEFAULT_REPORT, help="현재 mutations.xml")
    parser.add_argument("--state", default=verdict.DEFAULT_STATE, help="상태 파일")
    parser.add_argument("--scope", help="이번 실행이 본 범위 (기본: 전체)")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                        help=f"리포트를 쌓을 디렉터리 (기본: {DEFAULT_OUT_DIR}/)")
    parser.add_argument("-o", "--output", help="파일 경로를 직접 지정한다 (--out-dir 를 무시)")
    parser.add_argument("--stdout", action="store_true", help="파일 대신 표준 출력으로 낸다")
    args = parser.parse_args(argv)

    generated_at = datetime.now().astimezone()
    try:
        state = verdict.load_state(args.state)
        text = build(args.before, args.after, state, scope=args.scope, generated_at=generated_at)
        stale = stale_after(state, parse_mutations.parse_report(args.after))
    except (verdict.VerdictError, parse_mutations.MutationReportError) as error:
        print(f"error: {error}", file=sys.stderr)
        return verdict.EXIT_ERROR

    if stale:
        print(f"warning: 죽었다고 기록된 뮤턴트 {len(stale)}개가 {args.after} 에서 아직 살아 있다 "
              "— 리포트가 낡았는지 확인한다", file=sys.stderr)

    if args.stdout:
        print(text)
        return 0

    path = Path(args.output) if args.output else output_path(args.out_dir, generated_at)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
