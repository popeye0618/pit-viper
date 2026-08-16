package com.pitviper.order.policy;

import static org.assertj.core.api.Assertions.assertThat;

import com.pitviper.common.vo.Money;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("ShippingCalculator")
class ShippingCalculatorTest {

    private final ShippingCalculator calculator = new ShippingCalculator();

    @Test
    @DisplayName("무료배송 기준을 넘으면 배송비가 면제된다")
    void waivesFeeAboveThreshold() {
        assertThat(calculator.feeFor(Money.of(100_000), false)).isEqualTo(Money.ZERO);
    }

    @Test
    @DisplayName("기준과 같은 금액은 면제 대상이 아니다")
    void chargesFeeAtThreshold() {
        assertThat(calculator.feeFor(ShippingCalculator.FREE_THRESHOLD, false))
                .isEqualTo(ShippingCalculator.BASE_FEE);
    }

    @Test
    @DisplayName("도서산간 할증은 면제와 무관하게 붙는다")
    void islandSurchargeSurvivesWaiver() {
        // 기본 3_000 + 할증 5_000, 면제되면 할증만 남는다
        assertThat(calculator.feeFor(Money.of(10_000), true)).isEqualTo(Money.of(8_000));
        assertThat(calculator.feeFor(Money.of(100_000), true)).isEqualTo(Money.of(5_000));
    }

    @Test
    @DisplayName("배송비가 0원일 때만 무료배송이다")
    void freeShippingOnlyWhenFeeIsZero() {
        assertThat(calculator.isFreeShipping(Money.of(100_000), false)).isTrue();
        assertThat(calculator.isFreeShipping(Money.of(10_000), false)).isFalse();
        assertThat(calculator.isFreeShipping(Money.of(100_000), true)).isFalse();
    }

    @Test
    @DisplayName("배송 정책값이 정해진 대로 꽂혀 있다")
    void pinsPolicyConstants() {
        assertThat(ShippingCalculator.FREE_THRESHOLD).isEqualTo(Money.of(50_000));
        assertThat(ShippingCalculator.BASE_FEE).isEqualTo(Money.of(3_000));
        assertThat(ShippingCalculator.ISLAND_SURCHARGE).isEqualTo(Money.of(5_000));
    }
}
