package com.pitviper.order.service;

import com.pitviper.common.exception.BusinessException;
import com.pitviper.common.vo.Money;
import com.pitviper.customer.entity.Customer;
import com.pitviper.order.exception.OrderErrorCode;
import com.pitviper.order.policy.DiscountPolicy;
import com.pitviper.order.policy.PointPolicy;
import com.pitviper.order.policy.ShippingCalculator;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

/** 주문 금액 계산. */
@Service
@RequiredArgsConstructor
public class OrderService {

    public static final int MAX_QUANTITY = 100;

    private final DiscountPolicy discountPolicy;
    private final PointPolicy pointPolicy;
    private final ShippingCalculator shippingCalculator;

    /**
     * 최종 결제 금액 = (단가 × 수량) − 할인 + 배송비.
     *
     * <p>배송비는 할인 전 금액을 기준으로 계산한다. 할인 후 금액으로 판정하면 같은 장바구니가
     * 할인율에 따라 배송비 유무가 갈려 고객이 납득하기 어렵다.
     *
     * @throws BusinessException 수량이 1 미만이거나 {@link #MAX_QUANTITY} 를 초과할 때
     */
    public Money finalPrice(Customer customer, Money unitPrice, int quantity, boolean island) {
        if (quantity <= 0) {
            throw new BusinessException(OrderErrorCode.INVALID_QUANTITY);
        }
        if (quantity > MAX_QUANTITY) {
            throw new BusinessException(OrderErrorCode.QUANTITY_LIMIT_EXCEEDED);
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
