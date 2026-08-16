package com.pitviper.order.policy;

import static org.assertj.core.api.Assertions.assertThat;

import com.pitviper.common.vo.Money;
import com.pitviper.customer.entity.Customer;
import com.pitviper.customer.enums.Grade;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("DiscountPolicy")
class DiscountPolicyTest {

    private final DiscountPolicy policy = new DiscountPolicy();

    @Test
    @DisplayName("비회원은 등급 할인을 받지 못한다")
    void guestGetsNoGradeBonus() {
        assertThat(policy.rateFor(Customer.guest("g1"), Money.of(10_000))).isEqualTo(0.0);
    }

    @Test
    @DisplayName("회원은 등급 보너스만큼 할인받는다")
    void memberGetsGradeBonus() {
        assertThat(policy.rateFor(Customer.member("c1", Grade.SILVER), Money.of(10_000)))
                .isEqualTo(0.05);
        assertThat(policy.rateFor(Customer.member("c2", Grade.GOLD), Money.of(10_000)))
                .isEqualTo(0.10);
    }

    @Test
    @DisplayName("큰 주문 보너스는 기준을 넘어야 붙고 기준과 같으면 안 붙는다")
    void largeOrderBonusNeedsStrictlyMore() {
        Customer guest = Customer.guest("g1");

        assertThat(policy.rateFor(guest, DiscountPolicy.LARGE_ORDER_THRESHOLD)).isEqualTo(0.0);
        assertThat(policy.rateFor(guest, Money.of(200_000))).isEqualTo(0.10);
    }

    @Test
    @DisplayName("등급 보너스와 큰 주문 보너스는 합산된다")
    void bonusesAccumulate() {
        assertThat(policy.rateFor(Customer.member("c1", Grade.GOLD), Money.of(200_000)))
                .isEqualTo(0.20);
    }

    @Test
    @DisplayName("합산 할인율이 상한을 넘으면 상한으로 자른다")
    void capsAtMaxRate() {
        // VIP 0.20 + 큰 주문 0.10 = 0.30 이지만 상한은 0.25
        assertThat(policy.rateFor(Customer.member("c1", Grade.VIP), Money.of(200_000)))
                .isEqualTo(0.25);
    }

    @Test
    @DisplayName("할인 금액은 주문 금액에 할인율을 적용한 값이다")
    void discountAppliesRateToOrderAmount() {
        // SILVER 5% of 10_000
        assertThat(policy.discountFor(Customer.member("c1", Grade.SILVER), Money.of(10_000)))
                .isEqualTo(Money.of(500));
    }

    @Test
    @DisplayName("할인 정책값이 정해진 대로 꽂혀 있다")
    void pinsPolicyConstants() {
        assertThat(DiscountPolicy.LARGE_ORDER_THRESHOLD).isEqualTo(Money.of(100_000));
        assertThat(DiscountPolicy.LARGE_ORDER_BONUS).isEqualTo(0.10);
        assertThat(DiscountPolicy.MAX_RATE).isEqualTo(0.25);
    }
}
