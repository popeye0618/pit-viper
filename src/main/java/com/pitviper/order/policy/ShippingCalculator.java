package com.pitviper.order.policy;

import com.pitviper.common.vo.Money;
import org.springframework.stereotype.Component;

/** 배송비 계산. */
@Component
public class ShippingCalculator {

    public static final Money FREE_THRESHOLD = Money.of(50_000);
    public static final Money BASE_FEE = Money.of(3_000);
    public static final Money ISLAND_SURCHARGE = Money.of(5_000);

    /**
     * 주문 금액이 무료배송 기준을 넘으면 기본 배송비가 면제된다.
     *
     * <p>도서산간 할증은 면제와 무관하게 붙는다. 실제 운송비가 발생하는 구간이라 정책상 면제 대상이
     * 아니다.
     */
    public Money feeFor(Money orderAmount, boolean island) {
        Money fee = orderAmount.isGreaterThan(FREE_THRESHOLD) ? Money.ZERO : BASE_FEE;

        if (island) {
            fee = fee.plus(ISLAND_SURCHARGE);
        }
        return fee;
    }

    public boolean isFreeShipping(Money orderAmount, boolean island) {
        return feeFor(orderAmount, island).isZero();
    }
}
