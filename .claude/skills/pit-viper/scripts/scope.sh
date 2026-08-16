#!/usr/bin/env bash
#
# 브랜치가 바꾼 src/main 클래스만 골라 FQCN 으로 출력한다.
#
# 이 스킬의 비용은 pitest 가 지배한다. 전체를 스캔하면 실전 프로젝트에서는 몇 분이 아니라
# 몇십 분이 되므로, 대상을 "이 브랜치가 실제로 건드린 클래스"로 좁히는 것이 전제 조건이다.
#
# 파싱이 없고 git 호출과 문자열 가공이 전부라 셸로 썼다.
# 구조화된 데이터(XML)를 다루는 일은 파이썬 쪽에 있다.

# -e          명령이 실패하면 즉시 멈춘다. 없으면 git 이 실패해도 다음 줄이 그대로 굴러가
#             "변경된 클래스 없음"이라는 잘못된 결론을 내놓는다.
# -u          정의되지 않은 변수를 쓰면 에러. 오타난 변수가 빈 문자열로 조용히 넘어가는 것을 막는다.
# -o pipefail 파이프 중간이 실패해도 전체를 실패로 본다. 기본값은 마지막 명령의 종료 코드만 본다.
set -euo pipefail

SOURCE_ROOT="src/main/java"

# 종료 코드 규약 — SKILL.md 가 stdout 을 파싱하지 않고 분기할 수 있게 한다.
EXIT_ERROR=2
EXIT_NO_CHANGES=3

usage() {
    cat <<'USAGE'
사용: scope.sh [기준ref] [--pitest]

  기준ref     비교 기준 (기본: main). 이 ref 와의 공통 조상 이후 변경을 본다.
  --pitest    pitest targetClasses 에 넣을 콤마 목록으로 출력 (기본: 한 줄에 하나)

종료 코드: 0 목록 출력 · 2 오류 · 3 변경된 src/main 클래스 없음

예:
  scope.sh                    # main 대비 변경 클래스
  scope.sh origin/develop     # 다른 기준
  scope.sh main --pitest      # com.a.Foo,com.b.Bar
USAGE
}

die() {
    echo "error: $*" >&2
    exit "$EXIT_ERROR"
}

base="main"
format="lines"

while [ $# -gt 0 ]; do
    case "$1" in
        --pitest) format="pitest" ;;
        -h|--help) usage; exit 0 ;;
        -*) die "모르는 옵션: $1" ;;
        *) base="$1" ;;
    esac
    shift
done

git rev-parse --git-dir >/dev/null 2>&1 || die "git 저장소가 아니다"
git rev-parse --verify --quiet "$base^{commit}" >/dev/null \
    || die "기준 ref 를 찾을 수 없다: $base"

# 세 갈래를 합친다. 개발자의 로컬 루프는 커밋 전에도 돌아야 하므로
# 커밋된 변경만 보면 방금 쓴 코드가 스코프에서 빠진다.
#   1) 기준과의 공통 조상 이후 이 브랜치가 커밋한 것 (세 점 표기)
#   2) 아직 커밋하지 않은 것 (스테이징 + 워킹 트리)
#   3) 아직 git 이 모르는 새 파일
# --diff-filter=d 는 삭제된 파일을 뺀다. 사라진 클래스에는 뮤턴트를 심을 수 없다.
changed=$(
    {
        git diff --name-only --diff-filter=d "$base...HEAD"
        git diff --name-only --diff-filter=d HEAD
        git ls-files --others --exclude-standard
    } | sort -u
)

# grep 은 일치하는 줄이 없으면 종료 코드 1 을 낸다. set -e 아래에서는 그것만으로 스크립트가
# 죽으므로 || true 로 받아준다 — "변경 없음"은 오류가 아니다.
sources=$(printf '%s\n' "$changed" | grep -E "^${SOURCE_ROOT}/.+\.java$" || true)

if [ -z "$sources" ]; then
    echo "변경된 ${SOURCE_ROOT} 클래스가 없다 (기준: ${base})" >&2
    exit "$EXIT_NO_CHANGES"
fi

# src/main/java/com/pitviper/order/policy/PointPolicy.java
#   → com.pitviper.order.policy.PointPolicy
classes=$(printf '%s\n' "$sources" \
    | sed -e "s|^${SOURCE_ROOT}/||" -e 's|\.java$||' -e 's|/|.|g')

if [ "$format" = "pitest" ]; then
    # 중첩 클래스는 Outer$Inner 로 컴파일된다. pitest 의 targetClasses 글롭에서
    # com.a.Outer 는 com.a.Outer$Inner 를 잡지 못하므로 두 패턴을 함께 넣는다.
    #
    # 실측(harucut, sealed interface + record): 이 줄이 없으면 뮤턴트 7개,
    # 있으면 19개. 분기 로직이 전부 중첩 record 안에 있어서 대부분을 놓쳤다.
    printf '%s\n' "$classes" | awk '{ print $0; print $0 "$*" }' | paste -sd, -
else
    # 줄 목록은 사람과 다른 소비자를 위한 것이라 클래스 이름만 낸다.
    printf '%s\n' "$classes"
fi
