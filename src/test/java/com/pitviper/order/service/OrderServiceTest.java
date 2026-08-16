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
    @DisplayName("최종 금액은 할인을 빼고 배송비를 더한 값이다")
    void finalPriceSubtractsDiscountThenAddsShipping() {
        // 10_000 × 2 = 20_000 → SILVER 5% 할인 1_000 → 19_000 → 배송비 3_000
        assertThat(orderService.finalPrice(
                Customer.member("c1", Grade.SILVER), Money.of(10_000), 2, false))
                .isEqualTo(Money.of(22_000));
    }

    @Test
    @DisplayName("비회원은 할인 없이 배송비만 더해진다")
    void guestPaysGrossPlusShipping() {
        assertThat(orderService.finalPrice(Customer.guest("g1"), Money.of(10_000), 1, false))
                .isEqualTo(Money.of(13_000));
    }

    @Test
    @DisplayName("배송비는 할인 전 금액을 기준으로 판정한다")
    void shippingIsJudgedOnGrossAmount() {
        // 총액 60_000 은 무료배송 기준을 넘으므로, 할인 후 금액이 기준 아래여도 배송비가 없다
        assertThat(orderService.finalPrice(
                Customer.member("c1", Grade.VIP), Money.of(60_000), 1, false))
                .isEqualTo(Money.of(48_000));
    }

    @Test
    @DisplayName("수량이 1 미만이면 예외다")
    void rejectsNonPositiveQuantity() {
        Customer guest = Customer.guest("g1");

        assertThatThrownBy(() -> orderService.finalPrice(guest, Money.of(10_000), 0, false))
                .isInstanceOf(BusinessException.class);
        assertThatThrownBy(() -> orderService.finalPrice(guest, Money.of(10_000), -1, false))
                .isInstanceOf(BusinessException.class);
    }

    @Test
    @DisplayName("수량 상한까지는 주문할 수 있고 하나라도 넘으면 예외다")
    void quantityLimitIsInclusive() {
        Customer guest = Customer.guest("g1");

        assertThat(orderService.finalPrice(
                guest, Money.of(1_000), OrderService.MAX_QUANTITY, false))
                .isEqualTo(Money.of(100_000));
        assertThatThrownBy(() -> orderService.finalPrice(
                guest, Money.of(1_000), OrderService.MAX_QUANTITY + 1, false))
                .isInstanceOf(BusinessException.class);
    }

    @Test
    @DisplayName("적립은 실제 결제 금액을 기준으로 한다")
    void pointsAreBasedOnFinalPrice() {
        // 결제 22_000 → 220 포인트
        assertThat(orderService.pointsFor(
                Customer.member("c1", Grade.SILVER), Money.of(10_000), 2, false))
                .isEqualTo(220);
    }

    @Test
    @DisplayName("수량 상한이 정해진 대로 꽂혀 있다")
    void pinsQuantityLimit() {
        assertThat(OrderService.MAX_QUANTITY).isEqualTo(100);
    }
}
