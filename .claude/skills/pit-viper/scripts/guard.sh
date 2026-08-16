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
#
# 판정 기준은 "이번 실행 중에 바뀌었는가"이지 "커밋됐는가"가 아니다.
# 스킬이 도는 자리는 대개 아직 커밋하지 않은 새 기능 위라, HEAD 와 비교하면
# 에이전트가 건드리지도 않은 기존 작업을 위반으로 잡는다. 그래서 루프 시작 시점에
# `guard.sh snapshot` 으로 지문을 떠 두고 그것과 비교한다.

set -euo pipefail

EXIT_VIOLATION=1
EXIT_ERROR=2

DEFAULT_SNAPSHOT=".pit-viper/guard-snapshot.txt"

# 소비자 프로젝트가 구조를 달리 쓰면 이 환경 변수로 바꾼다.
GUARD_REGEX="${PIT_VIPER_GUARD_REGEX:-^(src/main/|build\.gradle(\.kts)?$|settings\.gradle(\.kts)?$|pom\.xml$)}"

usage() {
    cat <<'USAGE'
사용: guard.sh snapshot [--snapshot 경로]     루프 시작 시점의 보호 대상 지문을 뜬다
      guard.sh [--snapshot 경로] [--base ref] 그 뒤로 바뀌었는지 검사한다

  --snapshot 경로   지문 파일 (기본: .pit-viper/guard-snapshot.txt)
  --base ref        지문이 없을 때 쓰는 대체 기준. 해당 ref 이후 커밋까지 함께 본다

지문이 없으면 HEAD 와 비교한다. 그 경우 아직 커밋하지 않은 기존 작업도 위반으로 잡히므로,
루프를 시작할 때 snapshot 을 먼저 뜨는 것이 정상 사용법이다.

종료 코드: 0 위반 없음 · 1 금지된 파일이 바뀜 · 2 오류

환경 변수:
  PIT_VIPER_GUARD_REGEX   보호할 경로 패턴 (기본: src/main 과 빌드 파일)
USAGE
}

die() {
    echo "error: $*" >&2
    exit "$EXIT_ERROR"
}

command="check"
base=""
snapshot="$DEFAULT_SNAPSHOT"

while [ $# -gt 0 ]; do
    case "$1" in
        snapshot) command="snapshot" ;;
        --snapshot)
            [ $# -ge 2 ] || die "--snapshot 에 경로가 필요하다"
            snapshot="$2"; shift
            ;;
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

# 추적 여부와 무관하게 보호 대상 전부를 모은다.
# 아직 커밋하지 않은 새 파일도 에이전트가 고치면 위반이다.
list_guarded() {
    { git ls-files; git ls-files --others --exclude-standard; } | sort -u | grep -E "$GUARD_REGEX" || true
}

# git hash-object 를 쓰는 이유는 이미 git 을 요구하고 있어서다 —
# shasum/sha256sum 은 플랫폼마다 이름이 갈린다.
fingerprint() {
    local file
    list_guarded | while IFS= read -r file; do
        if [ -f "$file" ]; then
            printf '%s  %s\n' "$(git hash-object -- "$file")" "$file"
        fi
    done
}

report_violations() {
    echo "금지된 파일이 바뀌었다 — 테스트만 고쳐야 한다:" >&2
    printf '%s\n' "$1" | sed 's/^/  /' >&2
    exit "$EXIT_VIOLATION"
}

if [ "$command" = "snapshot" ]; then
    mkdir -p "$(dirname "$snapshot")"
    fingerprint > "$snapshot"
    echo "지문 $(wc -l < "$snapshot" | tr -d ' ')개를 떴다: $snapshot"
    exit 0
fi

if [ -f "$snapshot" ]; then
    current=$(fingerprint)
    # 한쪽에만 있는 줄 = 내용이 바뀌었거나, 새로 생겼거나, 사라진 파일.
    changed=$(
        { printf '%s\n' "$current"; cat "$snapshot"; } \
            | sort | uniq -u | awk '{ print $2 }' | sort -u
    )
    [ -z "$changed" ] || report_violations "$changed"
    echo "위반 없음 — 루프 시작 이후 src/main 과 빌드 파일이 그대로다"
    exit 0
fi

# 지문이 없을 때의 대체 경로. 커밋 여부로 판단하므로 기존 미커밋 작업도 걸린다.
if [ -n "$base" ]; then
    git rev-parse --verify --quiet "$base^{commit}" >/dev/null \
        || die "기준 ref 를 찾을 수 없다: $base"
fi

collect() {
    git diff --name-only HEAD
    git ls-files --others --exclude-standard
    if [ -n "$base" ]; then
        git diff --name-only "$base...HEAD"
    fi
}

# 수집과 걸러내기를 한 파이프에 묶지 않는다. 묶으면 git 이 실패해도 || true 가 함께 삼킨다.
collect_output=$(collect | sort -u)
violations=$(printf '%s\n' "$collect_output" | grep -E "$GUARD_REGEX" || true)

[ -z "$violations" ] || report_violations "$violations"
echo "위반 없음 — src/main 과 빌드 파일이 그대로다 (HEAD 기준)"
