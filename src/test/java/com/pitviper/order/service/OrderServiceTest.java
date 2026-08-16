package com.pitviper.order.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.pitviper.common.exception.BusinessException;
import com.pitviper.common.vo.Money;
import com.pitviper.customer.entity.Customer;
import com.pitviper.customer.enums.Grade;
import com.pitviper.order.policy.DiscountPolicy;
import com.pitviper.order.policy.PointPolicy;
import com.pitviper.order.policy.ShippingCalculator;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("OrderService")
class OrderServiceTest {

    private final OrderService orderService =
            new OrderService(new DiscountPolicy(), new PointPolicy(), new ShippingCalculator());

    @Test
    void 최종_금액을_계산한다() {
        Customer customer = Customer.member("c1", Grade.SILVER);

        Money price = orderService.finalPrice(customer, Money.of(10_000), 2, false);

        assertThat(price.amount()).isPositive();
    }

    @Test
    void 비회원도_주문할_수_있다() {
        Customer guest = Customer.guest("g1");

        Money price = orderService.finalPrice(guest, Money.of(10_000), 1, false);

        assertThat(price.amount()).isPositive();
    }

    @Test
    void 적립_포인트를_계산한다() {
        Customer customer = Customer.member("c1", Grade.SILVER);

        int points = orderService.pointsFor(customer, Money.of(10_000), 2, false);

        assertThat(points).isPositive();
    }

    @Test
    void 최종_금액은_할인을_빼고_배송비를_더한_값이다() {
        Customer customer = Customer.member("c1", Grade.SILVER);

        // 20_000 - 5% 할인 1_000 + 배송비 3_000
        Money price = orderService.finalPrice(customer, Money.of(10_000), 2, false);

        assertThat(price).isEqualTo(Money.of(22_000));
    }

    @Test
    void 수량이_0이면_예외다() {
        Customer guest = Customer.guest("g1");

        assertThatThrownBy(() -> orderService.finalPrice(guest, Money.of(10_000), 0, false))
                .isInstanceOf(BusinessException.class);
    }

    @Test
    void 수량_상한까지는_주문할_수_있다() {
        Customer guest = Customer.guest("g1");

        Money price =
                orderService.finalPrice(guest, Money.of(1_000), OrderService.MAX_QUANTITY, false);

        assertThat(price).isEqualTo(Money.of(100_000));
    }

    @Test
    void 수량_상한을_넘으면_예외다() {
        Customer guest = Customer.guest("g1");

        assertThatThrownBy(
                        () ->
                                orderService.finalPrice(
                                        guest, Money.of(1_000), OrderService.MAX_QUANTITY + 1, false))
                .isInstanceOf(BusinessException.class);
    }
}
