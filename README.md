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

두 신호는 대체재가 아니다. 이 저장소의 `ShippingCalculator`는 **라인·분기 커버리지가 둘 다 100%인데 생존 뮤턴트가 있다** —
Jacoco 쪽에서는 아무 문제가 보이지 않는 클래스다. 반대로 `GlobalExceptionHandler`의 미커버 16줄은 pitest 대상에도 없다.
그래서 둘 다 돌리되, 순서를 둔다.

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
.claude/skills/pit-viper/        스킬 본체 — 복사하면 그대로 도는 디렉터리
├── SKILL.md                     에이전트가 따르는 절차와 불변 규칙
├── scripts/                     결정적 도구 (파이썬 표준 라이브러리만, 설치 불필요)
│   ├── parse_mutations.py       mutations.xml → 생존 뮤턴트 JSON
│   ├── parse_jacoco.py          jacocoTestReport.xml → 미커버·부분분기 라인 JSON
│   ├── scope.sh                 브랜치 diff → 이번에 스캔할 클래스 목록
│   ├── verdict.py               전/후 대조 채점 + 시도 예산 강제 (state.json)
│   ├── report.py                최종 리포트 조립
│   └── guard.sh                 src/main·빌드 파일 수정 차단
└── tests/                       스크립트 자체 테스트 (프로젝트 테스트와 섞이지 않는다)
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

스킬을 이 저장소에 돌린 결과다. 3회전 만에 자력으로 종료했다.

| 지표 | 전 | 후 |
|---|---|---|
| 뮤테이션 스코어 | 66% (51/77) | **99% (76/77)** |
| 구멍 (생존 + 무커버) | 26 | **1** |
| 라인 커버리지 | 59/117 (50%) | **74/117 (63%)** |
| 분기 커버리지 | 28/44 (64%) | **40/44 (91%)** |

남은 1개는 **동등 뮤턴트**다 — `DiscountPolicy`의 할인율 상한 비교(`>` ↔ `>=`)인데, 등급 보너스 조합으로 도달 가능한 할인율이
`{0, 0.05, 0.1, 0.15, 0.2, 0.3}` 뿐이라 상한 `0.25`와 같아지는 입력이 없다. 사유와 함께 기록하고 목표에서 뺐다.
`src/main`은 한 줄도 수정하지 않았다.

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
- [ ] **S6** — 개인 스킬로 승격, 다른 프로젝트에 적용
