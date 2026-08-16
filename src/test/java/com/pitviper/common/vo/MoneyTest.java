package com.pitviper.common.vo;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("Money")
class MoneyTest {

    @Test
    void 금액을_만든다() {
        Money money = Money.of(1_000);

        assertThat(money.amount()).isEqualTo(1_000);
    }

    @Test
    void 더한다() {
        Money sum = Money.of(1_000).plus(Money.of(500));

        assertThat(sum.amount()).isEqualTo(1_500);
    }

    @Test
    void 뺀다() {
        Money rest = Money.of(1_000).minus(Money.of(300));

        assertThat(rest.amount()).isEqualTo(700);
    }

    @Test
    void 수량만큼_곱한다() {
        Money total = Money.of(1_000).times(3);

        assertThat(total.amount()).isEqualTo(3_000);
    }

    @Test
    void 비율을_적용한다() {
        Money discounted = Money.of(10_000).applyRate(0.1);

        assertThat(discounted.amount()).isEqualTo(1_000);
    }

    @Test
    void 더_큰_금액을_비교한다() {
        assertThat(Money.of(2_000).isGreaterThan(Money.of(1_000))).isTrue();
    }
}
