---
name: pit-viper
description: 테스트의 구멍을 찾아 메운다. Jacoco 로 미커버 코드를, pitest 로 생존 뮤턴트를 찾고 그것을 죽이는 테스트를 쓴 뒤 재실행 결과로 채점한다. "테스트 보강", "커버리지 올려줘", "뮤테이션 테스트", "테스트가 부실한 것 같다", "이 브랜치 테스트 점검" 같은 요청이나, 기능 구현을 끝내고 테스트 품질을 확인하려 할 때 쓴다. Jacoco 와 pitest 가 설정된 Gradle/Maven 프로젝트가 필요하다.
---

# pit-viper

테스트가 **있는데도 검증되지 않는 코드**를 찾아 메운다.

커버리지는 "이 줄이 실행됐는가"만 본다. 실행됐지만 아무것도 단언하지 않는 테스트도 커버리지는 올라간다.
뮤테이션 테스팅은 프로덕션 코드를 일부러 변형(뮤턴트)시켜 보고, **그래도 테스트가 통과하면 그 자리는 검증되지 않은 것**이라고 알려준다.

## 불변 규칙

이 넷은 절차보다 우선한다. 어기면 결과 전체가 무효다.

1. **`src/main` 과 빌드 파일을 수정하지 않는다.** 테스트를 통과시키려 프로덕션 코드를 고치는 것은 성과가 아니라 실패다. `build.gradle` 의 `excludedClasses` 로 뮤턴트를 지우는 것도 같다. 매 회전 끝에 `guard.sh` 로 확인한다.
2. **킬 판정은 `verdict.py` 출력만 신뢰한다.** "이 테스트면 죽을 것이다"라는 판단을 결과로 보고하지 않는다. 스크립트가 죽었다고 말하기 전까지 그 뮤턴트는 살아있다.
3. **목표는 스크립트가 준 목록에만 있다.** `next_targets` 에 없는 뮤턴트를 임의로 추가하지 않는다. 예산을 소진했거나 equivalent 로 닫힌 것이 그 목록에서 빠져 있는 것이다.
4. **테스트를 지우거나 약화시키지 않는다.** `verdict.py` 가 퇴행(전에 잡혔던 뮤턴트가 다시 살아남)을 종료 코드 1 로 알린다.

## 스크립트

전부 `.claude/skills/pit-viper/scripts/` 에 있고 파이썬 표준 라이브러리만 쓴다. 설치할 것이 없다.

| 스크립트 | 하는 일 |
|---|---|
| `scope.sh [기준ref] [--pitest]` | 브랜치가 바꾼 `src/main` 클래스 목록. 종료 코드 3 = 변경 없음 |
| `parse_jacoco.py [리포트]` | 미커버 라인 · 부분분기 라인 |
| `parse_mutations.py [리포트]` | 생존 뮤턴트 목록 |
| `verdict.py compare <전> <후>` | 킬 판정 + 예산 갱신 + `next_targets`. 종료 코드 1 = 퇴행 |
| `verdict.py equivalent <id> --reason <사유>` | 동등 뮤턴트를 사유와 함께 닫는다 |
| `guard.sh` | 금지된 파일이 바뀌었으면 종료 코드 1 |

## 절차

### 0. 범위를 정한다

```bash
SCOPE=$(.claude/skills/pit-viper/scripts/scope.sh main --pitest) || true
```

종료 코드 3 이면 이 브랜치가 바꾼 `src/main` 클래스가 없다는 뜻이다. **여기서 멈추고 사용자에게 알린다.**
전체를 스캔하고 싶다면 사용자가 명시적으로 요청해야 한다 — 실전 프로젝트에서 전체 pitest 는 몇십 분이 걸린다.

### 1. 싼 신호부터 — 커버리지

```bash
./gradlew test jacocoTestReport
python3 .claude/skills/pit-viper/scripts/parse_jacoco.py
```

`uncovered_lines` 는 **아무 테스트도 실행하지 않은 줄**, `partial_lines` 는 **실행은 됐지만 안 가본 분기가 있는 줄**이다.
뒤엣것이 커버리지 화면에서는 초록불로 보이면서 뮤턴트가 살아남는 자리다.

미커버 라인이 많은 클래스부터 테스트를 쓴다. 초 단위로 끝나는 신호이므로 여기서 큰 구멍을 먼저 메우면 비싼 pitest 를 덜 돌린다.

### 2. 비싼 신호 — 뮤테이션

```bash
cp build/reports/pitest/mutations.xml /tmp/pit-viper-before.xml   # 없으면 먼저 pitest 를 돌린다
./gradlew pitest -PpitScope="$SCOPE"
python3 .claude/skills/pit-viper/scripts/parse_mutations.py
```

`survivors` 의 각 항목이 좌표다.

```json
{
  "id": "com.pitviper.order.policy.PointPolicy#accrue:27:ConditionalsBoundary:25",
  "class": "com.pitviper.order.policy.PointPolicy",
  "method": "accrue", "line": 27,
  "mutator": "ConditionalsBoundary",
  "description": "changed conditional boundary",
  "tests_run": 3
}
```

`tests_run` 이 0 이면 그 줄에 테스트가 아예 닿지 않았다는 뜻이고, 0 보다 크면 **테스트는 있는데 단언이 약한 것**이다. 후자가 이 스킬의 주 대상이다.

### 3. 테스트를 쓴다

해당 소스 파일의 그 줄을 **먼저 읽는다.** 뮤테이터 이름만 보고 쓰지 않는다.
그리고 "이 변형을 넣었을 때 실패하는 테스트"를 쓴다 — 유형별 전략은 아래에 있다.

테스트는 `src/test` 의 대응 위치에 쓰고, 프로젝트의 기존 테스트 스타일(명명·단언 라이브러리·픽스처)을 따른다.

### 4. 재실행하고 채점받는다

```bash
./gradlew pitest -PpitScope="$SCOPE"
python3 .claude/skills/pit-viper/scripts/verdict.py compare /tmp/pit-viper-before.xml build/reports/pitest/mutations.xml
bash .claude/skills/pit-viper/scripts/guard.sh
```

`verdict.py` 가 종료 코드 1 을 내면 **퇴행이다.** 살아난 뮤턴트를 확인하고, 지웠거나 약화시킨 테스트를 되돌린다.
`guard.sh` 가 종료 코드 1 을 내면 **금지된 파일을 건드린 것이다.** 되돌린다.

### 5. 보고한다

`verdict.py` 의 `summary` 를 그대로 옮긴다. 킬 개수를 스스로 세지 않는다.
`next_targets` 가 남아 있으면 몇 개가 남았고 각각 몇 번의 시도가 남았는지 알린다.

## 뮤테이터 유형별 킬 전략

| 유형 | 죽이는 법 |
|---|---|
| `ConditionalsBoundary` | `<` ↔ `<=` 변형이다. **임계값과 정확히 같을 때**를 테스트한다. 경계 ±1 도 함께 |
| `NegateConditionals` | 조건이 뒤집힌다. **분기 양쪽을 각각** 검증한다 |
| `RemoveConditional_ORDER_ELSE` | 비교가 통째로 `false` 가 된다. 조건이 참일 때와 거짓일 때 **결과가 다름**을 단언한다 |
| `RemoveConditional_EQUAL_ELSE` | 같음 비교가 사라진다. 같을 때와 다를 때의 결과 차이를 단언한다 |
| `BooleanTrueReturnVals` | 항상 `true` 를 반환한다. `isXxx()` 가 **`false` 를 반환하는 경우**를 단언한다 |
| `BooleanFalseReturnVals` | 항상 `false` 를 반환한다. `true` 인 경우를 단언한다 |
| `Math` | 연산자가 바뀐다(`+`↔`-`, `*`↔`/`). **정확한 값**을 단언한다 |
| `PrimitiveReturns` | 반환값이 `0` 이 된다. 0 이 아닌 정확한 값을 단언한다 |
| `NullReturnVals` | 반환값이 `null` 이 된다. 반환된 객체의 **내용**을 단언한다 |
| `VoidMethodCalls` | 메서드 호출이 사라진다. 그 호출의 **부수 효과**를 단언한다 |

### 생존의 주범은 느슨한 단언이다

```java
assertThat(result).isPositive();          // 계산이 틀려도 통과한다 → Math·PrimitiveReturns 가 산다
assertThat(result).isNotNull();           // 내용이 틀려도 통과한다 → NullReturnVals 가 산다
assertThat(policy.accrue(c, m)).isNotZero();
```

```java
assertThat(result).isEqualTo(1_200);      // 값이 하나라도 틀리면 깨진다
assertThat(quote.total()).isEqualTo(Money.of(9_000));
```

**단언을 정확한 값으로 바꾸는 것만으로 상당수가 죽는다.**

### 경계값은 세 점을 찍는다

```java
// MIN_ACCRUAL_AMOUNT = 10_000, 조건은 amount < MIN_ACCRUAL_AMOUNT
accrue(9_999)   → 적립 없음     // 경계 바로 아래
accrue(10_000)  → 적립 있음     // 경계와 같을 때 ← ConditionalsBoundary 를 죽이는 지점
accrue(10_001)  → 적립 있음     // 경계 바로 위
```

가운데가 빠지면 `<` 를 `<=` 로 바꿔도 아무 테스트가 깨지지 않는다.

## equivalent 판정

**뮤턴트를 죽일 수 없는 경우가 있다.** 변형이 관측 가능한 차이를 만들지 않는 경우다.

```java
return member && grade == Grade.VIP;
// member 가 false 인 입력에서 두 번째 조건은 어차피 평가되지 않는다
```

이때만, 그리고 **정말 그럴 때만** 사유를 달아 닫는다.

```bash
python3 .claude/skills/pit-viper/scripts/verdict.py equivalent \
    'com.pitviper.customer.entity.Customer#isVip:26:RemoveConditional_EQUAL_ELSE:9' \
    --reason "member 가 false 면 두 번째 조건은 도달 불가 — 관측 가능한 차이가 없다"
```

사유는 **어떤 입력에서도 차이가 관측되지 않는 이유**여야 한다.
"테스트하기 어렵다", "시간이 부족하다"는 사유가 아니다 — 그런 것은 예산이 알아서 처리한다.

## 실패했을 때

- **테스트를 썼는데 뮤턴트가 안 죽었다** → 정상이다. `verdict.py` 가 시도 횟수를 세고, 예산(기본 3회)을 소진하면 목표에서 자동으로 뺀다. 같은 뮤턴트에 매달리지 않는다.
- **`gone` 경고가 떴다** → `src/main` 이 바뀌었거나 pitest 범위가 달라졌다. `guard.sh` 로 확인한다.
- **컴파일이 깨졌다** → 테스트만 되돌린다. `src/main` 은 손대지 않는다.
