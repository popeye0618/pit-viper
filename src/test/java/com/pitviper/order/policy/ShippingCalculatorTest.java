package com.pitviper.order.policy;

import static org.assertj.core.api.Assertions.assertThat;

import com.pitviper.common.vo.Money;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("ShippingCalculator")
class ShippingCalculatorTest {

    private final ShippingCalculator calculator = new ShippingCalculator();

    @Test
    void 기준_금액을_넘으면_무료배송이다() {
        Money fee = calculator.feeFor(Money.of(100_000), false);

        assertThat(fee.amount()).isZero();
    }

    @Test
    void 기준_금액에_못_미치면_배송비가_붙는다() {
        Money fee = calculator.feeFor(Money.of(10_000), false);

        assertThat(fee.amount()).isPositive();
    }

    @Test
    void 도서산간은_할증이_붙는다() {
        Money normal = calculator.feeFor(Money.of(10_000), false);
        Money island = calculator.feeFor(Money.of(10_000), true);

        assertThat(island.amount()).isGreaterThan(normal.amount());
    }

    @Test
    void 무료배송_여부를_알려준다() {
        assertThat(calculator.isFreeShipping(Money.of(100_000), false)).isTrue();
    }

    @Test
    void 배송비가_붙으면_무료배송이_아니다() {
        assertThat(calculator.isFreeShipping(Money.of(10_000), false)).isFalse();
    }

    @Test
    void 기준_금액과_같으면_배송비가_붙는다() {
        Money fee = calculator.feeFor(ShippingCalculator.FREE_THRESHOLD, false);

        assertThat(fee).isEqualTo(ShippingCalculator.BASE_FEE);
    }
}
