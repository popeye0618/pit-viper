# pit-viper

테스트가 **있는데도 검증되지 않는 코드**를 찾아서, AI 에이전트가 그 구멍을 메우는 테스트를 쓰고,
스크립트가 실제로 메워졌는지 채점하는 **Claude Code 스킬**.

---

## 문제

이 저장소의 스프링 프로젝트를 측정하면 이렇게 나온다.

```
라인 커버리지  50%   ← 테스트가 아예 없는 코드가 있다
뮤테이션 스코어 66%   ← 77개 중 26곳은 코드를 바꿔도 테스트가 안 깨진다
```

두 숫자는 **서로 다른 문제**를 말한다.

커버리지는 "이 줄이 실행됐는가"만 본다. 실행됐지만 아무것도 단언하지 않는 테스트도 커버리지는 올라간다.
뮤테이션 테스팅은 프로덕션 코드를 일부러 변형(뮤턴트)시켜 보고, **그래도 테스트가 통과하면 그 자리는 검증되지 않은 것**이라고 알려준다.

실제로 이 프로젝트의 `PointPolicy` 한 곳만 봐도 9개의 뮤턴트가 살아있다.
적립 하한선을 `<` 에서 `<=` 로 바꾸든, VIP 배수 분기를 통째로 지우든 테스트는 초록불이다.
뮤테이션 대상 클래스만 따지면 라인 커버리지가 **90%**인데도 그렇다.

## 접근

두 신호를 **싼 것부터** 순서대로 쓴다.

| 단계 | 도구 | 찾는 것 | 비용 |
|---|---|---|---|
| 1 | Jacoco | 테스트가 **아예 없는** 코드 | 초 단위 |
| 2 | pitest | 테스트는 있는데 **검증이 약한** 코드 | 분 단위 |

싼 신호로 큰 구멍을 먼저 메우면, 비싼 pitest를 돌리는 횟수가 줄어든다.

두 신호는 대체재가 아니다. 이 저장소에서 실제로 관측한 세 경우다.

| 자리 | Jacoco | pitest |
|---|---|---|
| `ShippingCalculator` | 라인·분기 100% — 이상 없음 | **생존 뮤턴트 1개** |
| `GlobalExceptionHandler` | **미커버 16줄** | 대상 밖 |
| `Money`의 생성자 가드 (`if (amount < 0)`) | **부분분기로 보인다** | **뮤턴트를 아예 안 만든다** |

세 번째가 특히 중요하다. pitest는 생성자에 뮤턴트를 만들지 않아서(아래 "원리적으로 못 보는 곳" 참고)
**뮤테이션 점수만 보면 영원히 보이지 않는 자리**인데, 싼 신호 쪽에서는 그냥 보인다.
그래서 둘 다 돌리되, 순서를 둔다.

## 설치

두 가지만 하면 된다. 스크립트는 **파이썬 표준 라이브러리만** 쓰므로 설치할 의존성이 없다.

### 1. 스킬을 놓는다

```bash
# 이 저장소를 clone 한 곳을 가리키게 한다. 심링크라 스킬을 고치면 바로 반영된다.
mkdir -p ~/.claude/skills
ln -sfn "$(pwd)/.claude/skills/pit-viper" ~/.claude/skills/pit-viper
```

프로젝트 안에서만 쓰려면 `.claude/skills/pit-viper/` 로 복사해도 된다.
개인 스킬(`~/.claude/skills/`)은 어느 프로젝트에서나 트리거되고, 프로젝트 스킬은 그 저장소에서만 뜬다.

### 2. 소비자 프로젝트의 `build.gradle` 에 신호원 둘을 켠다

이 저장소의 [build.gradle](build.gradle)이 레퍼런스다. 핵심만 옮기면:

```groovy
plugins {
    id 'jacoco'
    id 'info.solidsoft.pitest' version '1.19.0'
}

dependencies {
    pitest 'org.pitest:pitest-junit5-plugin:1.2.3'   // pitest 는 JUnit 5 를 이걸로 인식한다
}

jacocoTestReport {
    reports { xml.required = true }                  // ⚠️ XML 은 기본으로 꺼져 있다
}

pitest {
    // 스킬의 scope.sh 가 "이 브랜치가 바꾼 클래스"만 넣는 자리
    targetClasses = findProperty('pitScope')?.toString()?.tokenize(',') ?: ['com.example.*']

    // ⚠️ 반드시 명시한다. 안 주면 pitest 가 targetClasses 패턴으로 테스트도 고르기 때문에,
    //    스코프를 좁히는 순간 돌릴 테스트가 0개가 되어 전부 NO_COVERAGE 로 보고된다.
    targetTests = ['com.example.*']

    mutators = ['DEFAULTS', 'NEGATE_CONDITIONALS']   // DEFAULTS 에는 조건 반전이 없다
    outputFormats = ['XML', 'HTML']
    timestampedReports = false
    mutationThreshold = 0
}
```

`.gitignore` 에 `.pit-viper/` 를 넣는다 (루프 상태 파일). 리포트가 쌓이는 `viper/` 는 취향껏.

### 3. 부른다

```
테스트 좀 점검해줘
```

스킬이 브랜치 diff에서 스캔 범위를 잡고, 두 신호를 읽고, 테스트를 쓰고, 재실행 결과로 채점한 뒤
`viper/pit-viper-<날짜>-<시각>.md` 에 리포트를 남긴다.

첫 실행 때 `viper/test-style.md` 가 만들어진다. **테스트를 어떤 스타일로 쓸지 정하는 파일**이니
한 번 열어 팀 관례에 맞게 고쳐두면 그 뒤로는 그대로 따른다.

## 원리적으로 못 보는 곳

뮤테이션 테스팅은 "존재하는 로직을 비틀었을 때 테스트가 알아채는가"를 잰다.
정의상 다음은 점수가 100%여도 잡지 못한다. **이 한계를 모르고 쓰면 점수가 안전의 증거로 오독된다.**

**1. 생성자.** pitest는 `<init>`에 뮤턴트를 만들지 않는다 — 이 저장소와 실제 프로젝트 양쪽에서 실측으로 확인했다
(`excludedMethods`를 비워도 0건, 일반 클래스·record·enum 모두). 컴팩트 생성자나 팩토리의 검증 로직은
**신호가 아예 도달하지 않는 사각지대**다. `if (max < 0) throw` 가드는 뮤턴트가 없으므로,
가드가 `<`에서 `<=`로 바뀌어 합법 값이 죽는 회귀가 나도 점수에 아무 변화가 없다.

**2. 데이터의 실수.** 뮤턴트는 연산·분기·반환값 같은 코드에서만 생성된다.
enum 상수에 꽂힌 정책 값, 설정 기본값처럼 "데이터"가 틀린 것은 비틀 코드가 없다.
`BASIC` 요금제에 `Limited(0)` 대신 `Unlimited()`를 꽂아도 뮤테이션 점수는 만점이다.
이건 적용값을 리터럴로 고정하는 테스트(data pinning)의 몫이다.

**3. 없는 코드.** 뮤테이션은 있는 것을 비트는 도구라, 빠진 검증·빠진 분기·
한 번도 인스턴스화되지 않는 합법 경계값은 뮤턴트 자체가 존재하지 않는다.
"무엇이 빠졌는가"는 명세를 아는 사람만 안다.

**4. 테스트와 구현이 같이 틀리는 오해.** 기대값을 구현과 같은 연산으로 계산한
미러 단언(`assertThat(x.cutoffFrom(now)).isEqualTo(now.minusMonths(3))`)은 그 연산에 대한 오해를 잡을 수 없다.
뮤테이션이 재는 것은 "테스트가 구현 변화에 민감한가"이지 "구현이 명세와 맞는가"가 아니다.

정리하면 결함을 잡는 층이 셋이고 이 도구는 그중 하나다:
**모양의 실수는 타입/컴파일러가, 로직의 검증 구멍은 뮤테이션이,
값·명세의 실수는 사람이 쓰는 고정 테스트가 잡는다.**
이 도구는 두 번째 층을 자동화할 뿐, 나머지 두 층을 대체하지 않는다.

> 운영상 추가: `excludedClasses`로 제외한 패키지는 아예 측정 밖이다.
> `enums`·`dto`를 제외하는 관례는 2번 한계와 겹치므로, 제외한 곳에 데이터 고정 테스트가 있는지 별도로 확인할 것.

`SKILL.md`는 1·2·3번을 "목표 목록에 뜨지 않는 것"으로 명시하고, 4번을 금지 규칙으로 둔다 —
에이전트가 목표 목록만 보고 "다 끝냈다"고 보고하지 않게 하려는 것이다.

## 테스트 스타일은 프로젝트가 정한다

사람마다 테스트 쓰는 방식이 다르다. 스킬이 추측하는 대신 **파일 하나를 계약으로 둔다.**

```
viper/test-style.md      명명 · 구조 · 단언 규칙. 없으면 첫 실행 때 기본값이 깔린다
```

에이전트는 테스트를 쓰기 전에 이 파일을 읽고 **여기 적힌 대로만** 쓴다.
`@DisplayName`을 한국어로 쓸지, 메서드 이름을 영어로 쓸지, `@Nested`로 묶을지 —
전부 이 파일에서 정한다. 고쳐도 스킬이 되돌리지 않는다.

## 설계 원칙

이 프로젝트의 모든 결정은 아래 다섯 가지로 심사한다.

1. **AI를 채점자 없는 자리에 두지 않는다.** 에이전트의 입력은 스크립트가 뽑은 목표(뮤턴트 좌표·미커버 라인)이고, 출력은 기계가 채점(컴파일·테스트·pitest 재실행)한다. **에이전트는 자기 채점을 하지 않는다.**
2. **결정적 도구가 할 수 있는 일은 AI에게 시키지 않는다.** 파싱·선별·채점·리포트는 전부 Python 스크립트다. AI는 "테스트 작성"과 "equivalent 판정" 두 지점에만 있다.
3. **프롬프트는 코드다.** SKILL.md를 고치면 이 프로젝트에 다시 돌려 킬률이 유지되는지 확인한다.
4. **루프는 수렴해야 한다.** 시도 예산은 지침이 아니라 상태 파일을 관리하는 스크립트가 강제한다.
5. **에이전트는 `src/main`을 만지지 않는다.** 테스트를 통과시키려 프로덕션 코드를 고치는 것은 실패다. 루프 시작 시점의 지문과 대조해 guard 스크립트가 막는다 — 빌드 파일도 함께 본다.

## 이 저장소의 구조

루트가 곧 스프링 프로젝트다. 스킬이 설치된 소비자 프로젝트의 모습을 그대로 보여주기 위해서다.

```
build.gradle                     Jacoco + pitest 설정 — 소비자 프로젝트가 따라할 레퍼런스
.claude/skills/pit-viper/        스킬 본체 — 복사하면 그대로 도는 디렉터리
├── SKILL.md                     에이전트가 따르는 절차와 불변 규칙
├── scripts/                     결정적 도구 (파이썬 표준 라이브러리만, 설치 불필요)
│   ├── parse_mutations.py       mutations.xml → 생존 뮤턴트 JSON
│   ├── parse_jacoco.py          jacocoTestReport.xml → 미커버·부분분기 라인 JSON
│   ├── scope.sh                 브랜치 diff → 이번에 스캔할 클래스 목록
│   ├── verdict.py               전/후 대조 채점 + 시도 예산 강제 (state.json)
│   ├── style.py                 프로젝트의 테스트 스타일 규칙을 읽는다
│   ├── report.py                viper/ 에 리포트 조립
│   └── guard.sh                 src/main·빌드 파일 수정 차단 (루프 시작 지문 대비)
├── templates/test-style.md      스타일 규칙 기본값
└── tests/                       스크립트 자체 테스트 (프로젝트 테스트와 섞이지 않는다)
viper/
├── test-style.md                이 프로젝트의 테스트 스타일 — 고쳐 쓰는 파일
└── pit-viper-<날짜>-<시각>.md    실행 리포트가 쌓인다
src/main/java/com/pitviper/
├── common/
│   ├── exception/               ErrorCode · BusinessException · GlobalExceptionHandler
│   ├── response/                Response 봉투
│   └── vo/                      Money
├── customer/
│   ├── entity/                  Customer
│   └── enums/                   Grade
└── order/
    ├── controller/              견적 API
    ├── service/                 OrderService
    ├── policy/                  DiscountPolicy · PointPolicy · ShippingCalculator
    ├── dto/                     QuoteRequest · QuoteResponse
    └── exception/               OrderErrorCode
```

`src/test`는 같은 패키지 구조를 그대로 따라간다. 테스트는 해피 패스만 덮은 상태로 두었다 — **이 구멍이 스킬의 목표다.**

## 직접 돌려보기

```bash
./gradlew test jacocoTestReport pitest
```

- 커버리지 리포트: `build/reports/jacoco/test/html/index.html`
- 뮤테이션 리포트: `build/reports/pitest/index.html`

## 결과

스킬을 이 저장소에 돌린 결과다. **1회전에 25개를 죽이고 2회전에 자력 종료**했다.

| 지표 | 전 | 후 |
|---|---|---|
| 뮤테이션 스코어 | 66% (51/77) | **99% (76/77)** |
| 구멍 (생존 + 무커버) | 26 | **1** |
| 라인 커버리지 | 59/117 (50%) | **75/117 (64%)** |
| 분기 커버리지 | 28/44 (64%) | **42/44 (95%)** |
| 부분분기 라인 (실행됐지만 안 가본 분기) | 12 | **0** |

남은 1개는 **동등 뮤턴트**다 — `DiscountPolicy`의 할인율 상한 비교(`>` ↔ `>=`)인데, 등급 보너스 조합으로 도달 가능한 할인율이
`{0, 0.05, 0.1, 0.15, 0.2, 0.3}` 뿐이라 상한 `0.25`와 같아지는 입력이 없다. 사유와 함께 기록하고 목표에서 뺐다.
`src/main`은 한 줄도 수정하지 않았다.

리포트 전문은 [viper/](viper/)에 쌓인다.

<details>
<summary>지침을 고치면 결과가 달라진다 — 같은 기준선에서 두 번 돌린 기록</summary>

`SKILL.md`를 고칠 때마다 `baseline` 태그로 되돌려 같은 출발점에서 다시 돌린다(설계 원칙 3).
아래는 실전 피드백을 반영해 지침에 규칙 셋(**가드 경계 쌍 · 미러 단언 금지 · 데이터 고정**)을 더하기 전후다.

| | 규칙 추가 전 | 규칙 추가 후 |
|---|---|---|
| 1회전 킬 | 14 | **25** |
| 총 회전 | 3 | **2** |
| 분기 커버리지 | 40/44 | **42/44** |
| 부분분기 라인 | 2 | **0** |

최종 뮤테이션 스코어는 둘 다 99%다. **뮤테이션 점수가 보상하지 않는 개선이 있다**는 뜻이고,
그래서 아래 "원리적으로 못 보는 곳"을 함께 읽어야 한다.

</details>

## 다른 프로젝트에 돌려본 기록

통제된 무대(이 저장소)가 아니라 **답을 모르는 실제 프로젝트**에서도 돌려봤다.
프로덕션 클래스 135개짜리 스프링 프로젝트의 작업 브랜치에서, `scope.sh` 가 잡은 **변경 클래스 4개만** 스캔했다.

| | |
|---|---|
| 대상 | 구독 플랜 정책 (sealed interface + record, 테스트 없음) |
| 스캔 범위 | 변경 클래스 4개 / 전체 135개 |
| 결과 | 뮤턴트 19개 · **19개 전부 킬** (1회전) |
| `src/main` | 무수정 (`guard.sh` 통과) |

이 과정에서 실전에서만 드러나는 문제 셋을 찾아 고쳤다 — 어느 것도 이 저장소에서는 나타나지 않았다.

1. **중첩 클래스를 통째로 놓쳤다.** 중첩 클래스는 `Outer$Inner` 로 컴파일되는데 pitest 글롭에서
   `com.a.Outer` 는 그것을 잡지 못한다. 뮤턴트가 19개가 아니라 7개만 생성됐다.
   → `scope.sh` 가 `Outer$*` 를 함께 낸다.
2. **스코프를 좁히면 테스트가 0개가 됐다.** pitest 는 `targetTests` 를 안 주면 `targetClasses` 패턴으로
   테스트도 고른다. 검증되던 코드가 전부 미커버로 보고돼, 스코프 기능이 단순히 안 되는 게 아니라
   **에이전트에게 거짓 목표를 주는** 상태였다. → `targetTests` 를 필수 설정으로 문서화.
3. **guard 가 사용자의 기존 작업을 위반으로 잡았다.** HEAD 와 비교했기 때문인데, 스킬이 도는 자리는
   대개 아직 커밋하지 않은 새 기능 위다. → 루프 시작 시점에 `guard.sh snapshot` 으로 지문을 뜨고
   그것과 비교한다. 판정 기준은 "커밋됐는가"가 아니라 **"이번 실행 중에 바뀌었는가"** 다.

## 기준선

스킬을 개발하는 동안 `src/main`은 고정한다. 이 숫자가 곧 회귀 테스트의 기준이다.

```
뮤테이션   총 77 · KILLED 51 (66%) · SURVIVED 24 · NO_COVERAGE 2  → 구멍 26개
커버리지   LINE 59/117 (50%) · BRANCH 28/44 (63%)
```

이 상태는 `baseline` 태그에 고정돼 있다. **스킬을 고쳤으면 여기로 되돌려 다시 돌린다.**

```bash
rm -rf src/test && git checkout baseline -- src/test    # 약한 테스트로 되돌린다
./gradlew test jacocoTestReport pitest --rerun-tasks    # 77 · KILLED 51 · 구멍 26 이 나와야 한다
cp build/reports/pitest/mutations.xml .pit-viper/before.xml
# ... 스킬 실행 ...
python3 .claude/skills/pit-viper/scripts/report.py --before .pit-viper/before.xml
```

> ⚠️ `rm -rf` 를 빼면 안 된다. `git checkout <태그> -- <경로>` 는 **그 태그에 있는 파일만** 되돌리고,
> 이후에 추가된 테스트 파일은 디스크에 그대로 남는다. 그러면 출발점이 기준선이 아니게 되고 회귀 검증이 무의미해진다.

킬률이 **26개 중 16개(60%) 아래로 떨어지면 회귀**다. 원래 테스트로 돌아오려면 `rm -rf src/test && git checkout HEAD -- src/test`.

생존 뮤턴트 분포:

| 클래스 | 생존 | | 유형 | 생존 |
|---|---|---|---|---|
| PointPolicy | 9 | | ConditionalsBoundary | 9 |
| Money | 4 | | RemoveConditional_ORDER_ELSE | 6 |
| OrderService | 4 | | RemoveConditional_EQUAL_ELSE | 5 |
| DiscountPolicy | 3 | | NegateConditionals | 2 |
| Customer | 3 | | BooleanTrueReturnVals | 2 |
| Grade | 2 | | Math | 1 |
| ShippingCalculator | 1 | | PrimitiveReturns | 1 |

## 진행 상황

- [x] **S0** — 스프링 프로젝트 + Jacoco/pitest 설정 + 기준선 고정
- [x] **S1** — `parse_mutations.py` (뮤테이션 리포트 → 목표 목록)
- [x] **S2** — `parse_jacoco.py` + `scope.sh` (커버리지 구멍, 변경 클래스 스코프)
- [x] **S3** — `verdict.py` + `guard.sh` (채점자와 안전장치)
- [x] **S4** — `SKILL.md` 1회전 루프 · **1회전에 구멍 26 → 12 (킬 14, 스코어 66% → 84%)**
- [x] **S5** — 수렴 루프 · **구멍 26개 중 25개 킬 (96%)** · 3회전 자력 종료
- [x] **S6** — 개인 스킬로 승격, 다른 프로젝트에 적용 · **변경 클래스 4개만 스캔해 19/19 킬**
