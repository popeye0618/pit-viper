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

## 설계 원칙

이 프로젝트의 모든 결정은 아래 다섯 가지로 심사한다.

1. **AI를 채점자 없는 자리에 두지 않는다.** 에이전트의 입력은 스크립트가 뽑은 목표(뮤턴트 좌표·미커버 라인)이고, 출력은 기계가 채점(컴파일·테스트·pitest 재실행)한다. **에이전트는 자기 채점을 하지 않는다.**
2. **결정적 도구가 할 수 있는 일은 AI에게 시키지 않는다.** 파싱·선별·채점·리포트는 전부 Python 스크립트다. AI는 "테스트 작성"과 "equivalent 판정" 두 지점에만 있다.
3. **프롬프트는 코드다.** SKILL.md를 고치면 이 프로젝트에 다시 돌려 킬률이 유지되는지 확인한다.
4. **루프는 수렴해야 한다.** 시도 예산은 지침이 아니라 상태 파일을 관리하는 스크립트가 강제한다.
5. **에이전트는 `src/main`을 만지지 않는다.** 테스트를 통과시키려 프로덕션 코드를 고치는 것은 실패다. guard 스크립트가 diff를 검사한다.

## 이 저장소의 구조

루트가 곧 스프링 프로젝트다. 스킬이 설치된 소비자 프로젝트의 모습을 그대로 보여주기 위해서다.

```
build.gradle                     Jacoco + pitest 설정 — 소비자 프로젝트가 따라할 레퍼런스
.claude/skills/pit-viper/        스킬 본체 — SKILL.md + scripts/   ※ 아직 미구현
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

## 기준선

스킬을 개발하는 동안 `src/main`은 고정한다. 이 숫자가 곧 회귀 테스트의 기준이다.

```
뮤테이션   총 77 · KILLED 51 (66%) · SURVIVED 24 · NO_COVERAGE 2  → 구멍 26개
커버리지   LINE 59/117 (50%) · BRANCH 28/44 (63%)
```

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
- [ ] **S1** — `parse_mutations.py` (뮤테이션 리포트 → 목표 목록)
- [ ] **S2** — `parse_jacoco.py` + `scope.sh` (커버리지 구멍, 변경 클래스 스코프)
- [ ] **S3** — `verdict.py` + `guard.sh` (채점자와 안전장치)
- [ ] **S4** — `SKILL.md` 1회전 루프
- [ ] **S5** — 수렴 루프 · **구멍 26개 중 16개 이상 킬**
- [ ] **S6** — 개인 스킬로 승격, 다른 프로젝트에 적용
