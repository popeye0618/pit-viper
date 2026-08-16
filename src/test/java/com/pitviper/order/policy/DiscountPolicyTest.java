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
    void 회원은_등급_할인을_받는다() {
        Customer customer = Customer.member("c1", Grade.GOLD);

        double rate = policy.rateFor(customer, Money.of(10_000));

        assertThat(rate).isPositive();
    }

    @Test
    void 비회원은_등급_할인을_받지_못한다() {
        Customer guest = Customer.guest("g1");

        double rate = policy.rateFor(guest, Money.of(10_000));

        assertThat(rate).isZero();
    }

    @Test
    void 큰_주문은_추가_할인을_받는다() {
        Customer guest = Customer.guest("g1");

        double rate = policy.rateFor(guest, Money.of(200_000));

        assertThat(rate).isPositive();
    }

    @Test
    void 할인_금액을_계산한다() {
        Customer customer = Customer.member("c1", Grade.SILVER);

        Money discount = policy.discountFor(customer, Money.of(10_000));

        assertThat(discount.amount()).isPositive();
    }
}
