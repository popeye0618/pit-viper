#!/usr/bin/env bash
#
# 에이전트가 만지면 안 되는 파일이 바뀌었는지 검사한다. 하나라도 걸리면 실패한다.
#
# 원칙 5 의 구현체다. 이 스킬의 에이전트는 Edit 권한을 갖고 도는데, 테스트를 통과시키는
# 가장 쉬운 길은 언제나 프로덕션 코드를 고치는 것이다. 그건 성과가 아니라 실패다.
#
# 두 종류를 막는다:
#   1) src/main  — 검증 대상 자체를 바꾸는 것
#   2) 빌드 파일 — 측정 규칙을 바꾸는 것. excludedClasses 한 줄이면 생존 뮤턴트가 통째로
#      사라지고, 리포트상으로는 '해결'로 보인다. 코드를 고치는 것보다 더 조용한 우회로다.

set -euo pipefail

EXIT_VIOLATION=1
EXIT_ERROR=2

# 소비자 프로젝트가 구조를 달리 쓰면 이 환경 변수로 바꾼다.
GUARD_REGEX="${PIT_VIPER_GUARD_REGEX:-^(src/main/|build\.gradle(\.kts)?$|settings\.gradle(\.kts)?$|pom\.xml$)}"

usage() {
    cat <<'USAGE'
사용: guard.sh [--base ref]

  --base ref   해당 ref 이후의 커밋까지 함께 검사한다 (기본: 아직 커밋하지 않은 변경만)

종료 코드: 0 위반 없음 · 1 금지된 파일이 수정됨 · 2 오류

환경 변수:
  PIT_VIPER_GUARD_REGEX   보호할 경로 패턴 (기본: src/main 과 빌드 파일)
USAGE
}

die() {
    echo "error: $*" >&2
    exit "$EXIT_ERROR"
}

base=""

while [ $# -gt 0 ]; do
    case "$1" in
        --base)
            [ $# -ge 2 ] || die "--base 에 ref 가 필요하다"
            base="$2"; shift
            ;;
        -h|--help) usage; exit 0 ;;
        *) die "모르는 인자: $1" ;;
    esac
    shift
done

git rev-parse --git-dir >/dev/null 2>&1 || die "git 저장소가 아니다"

# 입력 검증은 파이프라인을 만들기 전에 끝낸다.
# 파이프 안에서 die 를 부르면 서브셸만 죽고, 그 실패가 아래 || true 에 삼켜진다.
if [ -n "$base" ]; then
    git rev-parse --verify --quiet "$base^{commit}" >/dev/null \
        || die "기준 ref 를 찾을 수 없다: $base"
fi

# 아직 커밋하지 않은 변경(스테이징 + 워킹 트리)과 새로 만든 파일.
# 에이전트는 커밋하지 않으므로 평소에는 이것만으로 충분하다.
collect() {
    git diff --name-only HEAD
    git ls-files --others --exclude-standard
    if [ -n "$base" ]; then
        git diff --name-only "$base...HEAD"
    fi
}

# 수집과 걸러내기를 한 파이프에 묶지 않는다. 묶으면 git 이 실패해도 || true 가 함께 삼킨다.
changed=$(collect | sort -u)

# grep 은 일치가 없으면 종료 코드 1 을 낸다. 여기서는 그게 '위반 없음'이라 || true 로 받는다.
violations=$(printf '%s\n' "$changed" | grep -E "$GUARD_REGEX" || true)

if [ -n "$violations" ]; then
    echo "금지된 파일이 수정됐다 — 테스트만 고쳐야 한다:" >&2
    printf '%s\n' "$violations" | sed 's/^/  /' >&2
    exit "$EXIT_VIOLATION"
fi

echo "위반 없음 — src/main 과 빌드 파일이 그대로다"
