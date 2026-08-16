package dev.pitviper.shop.service;

import static org.assertj.core.api.Assertions.assertThat;

import dev.pitviper.shop.domain.Customer;
import dev.pitviper.shop.domain.DiscountPolicy;
import dev.pitviper.shop.domain.Grade;
import dev.pitviper.shop.domain.Money;
import dev.pitviper.shop.domain.PointPolicy;
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
}
