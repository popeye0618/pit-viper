package dev.pitviper.shop.domain;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("PointPolicy")
class PointPolicyTest {

    private final PointPolicy policy = new PointPolicy();

    @Test
    void 결제_금액만큼_적립한다() {
        Customer customer = Customer.member("c1", Grade.SILVER);

        int points = policy.accrue(customer, Money.of(10_000));

        assertThat(points).isEqualTo(100);
    }

    @Test
    void 소액_결제는_적립하지_않는다() {
        Customer customer = Customer.member("c1", Grade.SILVER);

        int points = policy.accrue(customer, Money.of(500));

        assertThat(points).isZero();
    }

    @Test
    void 보유_포인트가_충분하면_사용할_수_있다() {
        assertThat(policy.canRedeem(1_000, 500)).isTrue();
    }

    @Test
    void 보유_포인트가_모자라면_사용할_수_없다() {
        assertThat(policy.canRedeem(100, 500)).isFalse();
    }
}
