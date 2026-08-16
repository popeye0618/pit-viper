#!/usr/bin/env python3
"""전/후 뮤테이션 리포트를 대조해 킬을 판정하고, 시도 예산을 강제한다.

이 스크립트가 원칙 1(채점자)과 원칙 4(수렴)의 구현체다.

- **에이전트는 자기 채점을 하지 않는다.** 킬 판정은 여기서만 나온다.
- **예산은 지침이 아니라 상태 파일이 강제한다.** 예산을 소진한 뮤턴트는 `next_targets` 에서
  기계적으로 빠지므로, 에이전트가 예산을 '잊어도' 무한 재시도가 불가능하다.

사용:
    verdict.py compare <전> <후> [--state 경로] [--budget N]
    verdict.py equivalent <뮤턴트id> --reason "사유" [--report 경로]
"""

import argparse
import json
import sys
from pathlib import Path

# 파이썬은 실행한 스크립트가 있는 디렉터리를 sys.path 맨 앞에 넣는다.
# 그래서 같은 scripts/ 안의 모듈은 설치나 경로 조작 없이 그대로 import 된다.
import parse_mutations

DEFAULT_STATE = ".pit-viper/state.json"
DEFAULT_REPORT = parse_mutations.DEFAULT_REPORT
DEFAULT_BUDGET = 3
STATE_VERSION = 1

EXIT_REGRESSION = 1
EXIT_ERROR = 2

# 상태 파일의 outcome 값
SURVIVING = "surviving"
KILLED = "killed"
EXHAUSTED = "exhausted"
EQUIVALENT = "equivalent"
GONE = "gone"

# 목표 목록에서 기계적으로 빠지는 상태.
# '포기'가 두 종류인 것이 중요하다 — 예산 소진은 기계가, equivalent 는 사람/에이전트가 사유를 달고 닫는다.
CLOSED = frozenset({EXHAUSTED, EQUIVALENT})


class VerdictError(Exception):
    """판정을 신뢰할 수 없는 상태일 때 던진다."""


def new_entry():
    return {"attempts": 0, "outcome": SURVIVING, "last_run": 0}


def load_state(path, budget=None):
    """상태 파일을 읽는다. 없으면 새로 시작한다."""
    path = Path(path)
    if not path.is_file():
        return {"version": STATE_VERSION, "budget": budget or DEFAULT_BUDGET, "run": 0, "mutants": {}}

    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise VerdictError(f"상태 파일이 깨졌다: {path} ({error})") from error

    if state.get("version") != STATE_VERSION:
        raise VerdictError(
            f"상태 파일 버전이 다르다: {state.get('version')} (기대: {STATE_VERSION}) — "
            f"{path} 를 지우고 다시 시작한다"
        )
    if budget is not None:
        # 명시적으로 준 예산이 저장된 값을 이긴다. 안 주면 저장된 값을 그대로 쓴다.
        state["budget"] = budget
    return state


def save_state(path, state):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys 로 항상 같은 순서를 쓴다 — 이 파일의 diff 가 곧 감사 로그다.
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def compare(before_path, after_path, state):
    """전/후를 안정 id 로 대조하고 상태 파일을 갱신한 뒤 판정 결과를 돌려준다."""
    before = parse_mutations.parse_report(before_path, include_all=True)
    after = parse_mutations.parse_report(after_path, include_all=True)

    before_all = {m["id"]: m for m in before["all"]}
    after_all = {m["id"]: m for m in after["all"]}
    before_surviving = {m["id"] for m in before["survivors"]}
    after_surviving = {m["id"]: m for m in after["survivors"]}

    # 뮤턴트 하나가 갈 수 있는 길은 다섯 가지다.
    killed = [i for i in before_surviving if i in after_all and i not in after_surviving]
    still_surviving = [i for i in before_surviving if i in after_surviving]
    gone = [i for i in before_surviving if i not in after_all]
    regressed = [i for i in after_surviving if i in before_all and i not in before_surviving]
    new = [i for i in after_surviving if i not in before_all]
    for bucket in (killed, still_surviving, gone, regressed, new):
        bucket.sort()

    state["run"] += 1
    mutants = state["mutants"]
    budget = state["budget"]

    for mutant_id in killed:
        entry = mutants.setdefault(mutant_id, new_entry())
        entry["outcome"] = KILLED
        entry["last_run"] = state["run"]

    for mutant_id in still_surviving:
        entry = mutants.setdefault(mutant_id, new_entry())
        if entry["outcome"] in CLOSED:
            # 이미 닫힌 목표다. 에이전트에게 준 적이 없으니 시도로 세지 않는다.
            continue
        entry["attempts"] += 1
        entry["outcome"] = EXHAUSTED if entry["attempts"] >= budget else SURVIVING
        entry["last_run"] = state["run"]

    for mutant_id in new + regressed:
        entry = mutants.setdefault(mutant_id, new_entry())
        if entry["outcome"] not in CLOSED:
            entry["outcome"] = SURVIVING
        entry["last_run"] = state["run"]

    for mutant_id in gone:
        entry = mutants.setdefault(mutant_id, new_entry())
        entry["outcome"] = GONE
        entry["last_run"] = state["run"]

    # 다음 회전의 목표. 닫힌 뮤턴트는 여기서 빠지고, 그래서 재시도가 물리적으로 불가능하다.
    targets = []
    for mutant_id, mutant in after_surviving.items():
        entry = mutants[mutant_id]
        if entry["outcome"] in CLOSED:
            continue
        targets.append({
            **mutant,
            "attempts": entry["attempts"],
            "attempts_left": max(budget - entry["attempts"], 0),
        })

    warnings = []
    if gone:
        # 안정 id 의 indexes 는 메서드 본문이 바뀌면 밀린다. src/main 이 고정이라면 밀릴 일이 없다.
        warnings.append(
            f"전 리포트에 있던 뮤턴트 {len(gone)}개가 후 리포트에 없다 — "
            "src/main 이 수정됐거나(guard.sh 로 확인) pitest 대상 범위가 달라졌다."
        )
    if regressed:
        warnings.append(
            f"전에 잡혔던 뮤턴트 {len(regressed)}개가 다시 살아났다 — "
            "기존 테스트가 약해졌거나 지워졌다."
        )

    closed_now = {
        "exhausted": sorted(i for i, e in mutants.items() if e["outcome"] == EXHAUSTED),
        "equivalent": sorted(i for i, e in mutants.items() if e["outcome"] == EQUIVALENT),
    }

    return {
        "before": str(before_path),
        "after": str(after_path),
        "run": state["run"],
        "budget": budget,
        "summary": {
            "before_gaps": len(before_surviving),
            "after_gaps": len(after_surviving),
            "killed": len(killed),
            "still_surviving": len(still_surviving),
            "gone": len(gone),
            "regressed": len(regressed),
            "new": len(new),
            "exhausted": len(closed_now["exhausted"]),
            "equivalent": len(closed_now["equivalent"]),
            "next_targets": len(targets),
        },
        "killed": killed,
        "still_surviving": still_surviving,
        "gone": gone,
        "regressed": regressed,
        "new": new,
        "closed": closed_now,
        "next_targets": targets,
        "warnings": warnings,
    }


def mark_equivalent(state, mutant_id, reason, report_path):
    """동등 뮤턴트로 판정된 것을 사유와 함께 닫는다.

    사유를 강제하는 이유는 원칙 4다. 사유 없이 닫을 수 있으면 'equivalent' 가
    막다른 뮤턴트를 치우는 편한 핑계가 되고, 수렴이 조용한 포기로 변질된다.
    """
    reason = (reason or "").strip()
    if not reason:
        raise VerdictError("사유 없이 equivalent 로 닫을 수 없다 — 조용한 포기를 막는다")

    survivors = {m["id"] for m in parse_mutations.parse_report(report_path)["survivors"]}
    if mutant_id not in survivors:
        # 오타난 id 를 그대로 받으면 아무것도 닫지 못한 채 닫았다고 믿게 된다.
        raise VerdictError(f"{report_path} 의 생존 뮤턴트에 없는 id 다: {mutant_id}")

    entry = state["mutants"].setdefault(mutant_id, new_entry())
    entry["outcome"] = EQUIVALENT
    entry["reason"] = reason
    entry["last_run"] = state["run"]
    return entry


def _build_parser():
    parser = argparse.ArgumentParser(description="뮤테이션 전/후 대조 채점자")
    parser.add_argument("--state", default=DEFAULT_STATE, help=f"상태 파일 (기본: {DEFAULT_STATE})")
    # 하위 명령. 하는 일이 '판정'과 '닫기'로 확실히 갈려서 플래그 대신 이 형태를 썼다.
    sub = parser.add_subparsers(dest="command", required=True)

    compare_cmd = sub.add_parser("compare", help="전/후 리포트를 대조해 판정한다")
    compare_cmd.add_argument("before", help="에이전트 작업 전 mutations.xml")
    compare_cmd.add_argument("after", help="에이전트 작업 후 mutations.xml")
    compare_cmd.add_argument("--budget", type=int, default=None,
                             help=f"뮤턴트당 시도 한도 (처음 실행 시 기본: {DEFAULT_BUDGET})")
    compare_cmd.add_argument("-o", "--output", help="판정 결과를 쓸 파일 (기본: 표준 출력)")

    equivalent_cmd = sub.add_parser("equivalent", help="동등 뮤턴트를 사유와 함께 닫는다")
    equivalent_cmd.add_argument("mutant_id", help="닫을 뮤턴트의 안정 id")
    equivalent_cmd.add_argument("--reason", required=True, help="왜 동등 뮤턴트인지 (필수)")
    equivalent_cmd.add_argument("--report", default=DEFAULT_REPORT,
                                help=f"id 를 검증할 리포트 (기본: {DEFAULT_REPORT})")
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)

    try:
        if args.command == "compare":
            state = load_state(args.state, args.budget)
            result = compare(args.before, args.after, state)
            save_state(args.state, state)

            text = json.dumps(result, ensure_ascii=False, indent=2)
            if args.output:
                Path(args.output).write_text(text + "\n", encoding="utf-8")
            else:
                print(text)

            summary = result["summary"]
            print(
                f"킬 {summary['killed']} · 생존 {summary['still_surviving']} · "
                f"예산소진 {summary['exhausted']} · 동등 {summary['equivalent']} → "
                f"다음 목표 {summary['next_targets']}",
                file=sys.stderr,
            )
            for warning in result["warnings"]:
                print(f"warning: {warning}", file=sys.stderr)

            # 퇴행은 넘어가면 안 되는 실패다. 리포트는 그대로 내주되 종료 코드로 알린다.
            return EXIT_REGRESSION if result["regressed"] else 0

        state = load_state(args.state)
        entry = mark_equivalent(state, args.mutant_id, args.reason, args.report)
        save_state(args.state, state)
        print(f"닫았다: {args.mutant_id}\n  사유: {entry['reason']}")
        return 0

    except (VerdictError, parse_mutations.MutationReportError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
