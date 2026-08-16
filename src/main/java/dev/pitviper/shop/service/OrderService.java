package dev.pitviper.shop.service;

import dev.pitviper.shop.domain.Customer;
import dev.pitviper.shop.domain.DiscountPolicy;
import dev.pitviper.shop.domain.Money;
import dev.pitviper.shop.domain.PointPolicy;
import org.springframework.stereotype.Service;

/** 주문 금액 계산. */
@Service
public class OrderService {

    public static final int MAX_QUANTITY = 100;

    private final DiscountPolicy discountPolicy;
    private final PointPolicy pointPolicy;
    private final ShippingCalculator shippingCalculator;

    public OrderService(
            DiscountPolicy discountPolicy,
            PointPolicy pointPolicy,
            ShippingCalculator shippingCalculator) {
        this.discountPolicy = discountPolicy;
        this.pointPolicy = pointPolicy;
        this.shippingCalculator = shippingCalculator;
    }

    /**
     * 최종 결제 금액 = (단가 × 수량) − 할인 + 배송비.
     *
     * <p>배송비는 할인 전 금액을 기준으로 계산한다. 할인 후 금액으로 판정하면 같은 장바구니가
     * 할인율에 따라 배송비 유무가 갈려 고객이 납득하기 어렵다.
     *
     * @throws IllegalArgumentException 수량이 1 미만이거나 {@link #MAX_QUANTITY} 를 초과할 때
     */
    public Money finalPrice(Customer customer, Money unitPrice, int quantity, boolean island) {
        if (quantity <= 0) {
            throw new IllegalArgumentException("수량은 1 이상이어야 한다: " + quantity);
        }
        if (quantity > MAX_QUANTITY) {
            throw new IllegalArgumentException("1회 주문 수량 상한을 넘었다: " + quantity);
        }

        Money gross = unitPrice.times(quantity);
        Money discounted = gross.minus(discountPolicy.discountFor(customer, gross));
        return discounted.plus(shippingCalculator.feeFor(gross, island));
    }

    /** 이 주문으로 적립될 포인트. 적립은 실제 결제 금액을 기준으로 한다. */
    public int pointsFor(Customer customer, Money unitPrice, int quantity, boolean island) {
        return pointPolicy.accrue(customer, finalPrice(customer, unitPrice, quantity, island));
    }
}
