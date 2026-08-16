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

    @Test
    void 등급_보너스가_할인율에_그대로_반영된다() {
        assertThat(policy.rateFor(Customer.member("c1", Grade.SILVER), Money.of(10_000)))
                .isEqualTo(Grade.SILVER.getBonusRate());
        assertThat(policy.rateFor(Customer.member("c2", Grade.GOLD), Money.of(10_000)))
                .isEqualTo(Grade.GOLD.getBonusRate());
    }

    @Test
    void 큰_주문_보너스와_등급_보너스는_합산된다() {
        Customer gold = Customer.member("c1", Grade.GOLD);

        double rate = policy.rateFor(gold, Money.of(200_000));

        assertThat(rate).isEqualTo(DiscountPolicy.LARGE_ORDER_BONUS + Grade.GOLD.getBonusRate());
    }

    @Test
    void 합산한_할인율이_상한을_넘으면_상한으로_자른다() {
        Customer vip = Customer.member("c1", Grade.VIP);

        double rate = policy.rateFor(vip, Money.of(200_000));

        assertThat(rate).isEqualTo(DiscountPolicy.MAX_RATE);
    }

    @Test
    void 큰_주문_기준과_같은_금액은_추가_할인을_받지_못한다() {
        Customer guest = Customer.guest("g1");

        double rate = policy.rateFor(guest, DiscountPolicy.LARGE_ORDER_THRESHOLD);

        assertThat(rate).isZero();
    }
}
