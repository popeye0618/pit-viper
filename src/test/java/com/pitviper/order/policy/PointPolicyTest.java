package com.pitviper.order.policy;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.pitviper.common.exception.BusinessException;
import com.pitviper.common.vo.Money;
import com.pitviper.customer.entity.Customer;
import com.pitviper.customer.enums.Grade;
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

    @Test
    void 적립_하한과_같은_금액은_적립한다() {
        Customer customer = Customer.member("c1", Grade.SILVER);

        int points = policy.accrue(customer, Money.of(PointPolicy.MIN_ACCRUAL_AMOUNT));

        assertThat(points).isEqualTo(10);
    }

    @Test
    void 적립_하한보다_1원_적으면_적립하지_않는다() {
        Customer customer = Customer.member("c1", Grade.SILVER);

        int points = policy.accrue(customer, Money.of(PointPolicy.MIN_ACCRUAL_AMOUNT - 1));

        assertThat(points).isZero();
    }

    @Test
    void VIP는_두_배로_적립한다() {
        Customer vip = Customer.member("c1", Grade.VIP);

        int points = policy.accrue(vip, Money.of(10_000));

        assertThat(points).isEqualTo(200);
    }

    @Test
    void 보유_포인트와_사용_포인트가_같으면_사용할_수_있다() {
        assertThat(policy.canRedeem(500, 500)).isTrue();
    }

    @Test
    void 사용_포인트가_0이면_예외다() {
        assertThatThrownBy(() -> policy.canRedeem(1_000, 0))
                .isInstanceOf(BusinessException.class);
    }

    @Test
    void GOLD_이상_회원은_소액이어도_적립한다() {
        Customer gold = Customer.member("c1", Grade.GOLD);

        int points = policy.accrue(gold, Money.of(500));

        assertThat(points).isEqualTo(5);
    }

    @Test
    void GOLD_미만_회원은_소액이면_적립하지_않는다() {
        Customer silver = Customer.member("c1", Grade.SILVER);

        int points = policy.accrue(silver, Money.of(500));

        assertThat(points).isZero();
    }

    @Test
    void 비회원은_등급이_높아도_하한_면제를_받지_못한다() {
        Customer nonMember = new Customer("g1", Grade.GOLD, false);

        int points = policy.accrue(nonMember, Money.of(500));

        assertThat(points).isZero();
    }
}
