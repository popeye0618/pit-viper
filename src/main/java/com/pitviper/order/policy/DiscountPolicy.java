package com.pitviper.order.policy;

import com.pitviper.common.vo.Money;
import com.pitviper.customer.entity.Customer;
import org.springframework.stereotype.Component;

/**
 * 할인율 정책. 큰 주문 보너스와 회원 등급 보너스를 더하되 상한을 넘지 않는다.
 *
 * <p>보너스를 더한 뒤 마지막에 상한을 적용하는 순서를 지킨다. 각 보너스에 개별 상한을 두면
 * 정책을 추가할 때마다 상한 계산이 갈라지기 때문이다.
 */
@Component
public class DiscountPolicy {

    public static final Money LARGE_ORDER_THRESHOLD = Money.of(100_000);
    public static final double LARGE_ORDER_BONUS = 0.10;
    public static final double MAX_RATE = 0.25;

    /** 이 고객·주문 금액에 적용될 할인율. 0.0 이상 {@link #MAX_RATE} 이하. */
    public double rateFor(Customer customer, Money orderAmount) {
        double rate = 0.0;

        if (orderAmount.isGreaterThan(LARGE_ORDER_THRESHOLD)) {
            rate += LARGE_ORDER_BONUS;
        }

        if (customer.member()) {
            rate += customer.grade().getBonusRate();
        }

        if (rate > MAX_RATE) {
            return MAX_RATE;
        }
        return rate;
    }

    /** 할인 금액. */
    public Money discountFor(Customer customer, Money orderAmount) {
        return orderAmount.applyRate(rateFor(customer, orderAmount));
    }
}
