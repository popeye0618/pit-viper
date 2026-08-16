package com.pitviper.common.vo;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

@DisplayName("Money")
class MoneyTest {

    @Nested
    @DisplayName("생성")
    class CreationTest {

        @Test
        @DisplayName("0원은 합법이다")
        void acceptsZero() {
            assertThat(Money.of(0).amount()).isZero();
        }

        @Test
        @DisplayName("음수 금액은 만들 수 없다")
        void rejectsNegativeAmount() {
            assertThatThrownBy(() -> Money.of(-1))
                    .isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Nested
    @DisplayName("산술")
    class ArithmeticTest {

        @Test
        @DisplayName("더하면 두 금액의 합이 된다")
        void addsAmounts() {
            assertThat(Money.of(1_000).plus(Money.of(500))).isEqualTo(Money.of(1_500));
        }

        @Test
        @DisplayName("빼면 두 금액의 차가 된다")
        void subtractsAmounts() {
            assertThat(Money.of(1_000).minus(Money.of(300))).isEqualTo(Money.of(700));
        }

        @Test
        @DisplayName("같은 금액을 빼면 0원이 된다")
        void subtractingEqualAmountGivesZero() {
            assertThat(Money.of(1_000).minus(Money.of(1_000))).isEqualTo(Money.ZERO);
        }

        @Test
        @DisplayName("가진 것보다 1원이라도 많이 빼면 예외다")
        void rejectsSubtractionBelowZero() {
            assertThatThrownBy(() -> Money.of(1_000).minus(Money.of(1_001)))
                    .isInstanceOf(IllegalStateException.class);
        }

        @Test
        @DisplayName("수량만큼 곱한다")
        void multipliesByQuantity() {
            assertThat(Money.of(1_000).times(3)).isEqualTo(Money.of(3_000));
        }

        @Test
        @DisplayName("비율을 적용하고 원 단위로 반올림한다")
        void appliesRateRoundingToWon() {
            assertThat(Money.of(10_000).applyRate(0.1)).isEqualTo(Money.of(1_000));
            // 502.5 는 503 으로 올라간다
            assertThat(Money.of(1_005).applyRate(0.5)).isEqualTo(Money.of(503));
        }
    }

    @Nested
    @DisplayName("비교")
    class ComparisonTest {

        @Test
        @DisplayName("더 클 때만 참이고 같으면 거짓이다")
        void comparesStrictlyGreater() {
            assertThat(Money.of(2_000).isGreaterThan(Money.of(1_000))).isTrue();
            assertThat(Money.of(1_000).isGreaterThan(Money.of(1_000))).isFalse();
            assertThat(Money.of(999).isGreaterThan(Money.of(1_000))).isFalse();
        }

        @Test
        @DisplayName("0원만 0원으로 판별한다")
        void detectsZeroOnly() {
            assertThat(Money.ZERO.isZero()).isTrue();
            assertThat(Money.of(1).isZero()).isFalse();
        }
    }
}
