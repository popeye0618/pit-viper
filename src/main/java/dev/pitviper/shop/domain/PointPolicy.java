package dev.pitviper.shop.domain;

import org.springframework.stereotype.Component;

/** 적립금 정책. */
@Component
public class PointPolicy {

    public static final int POINT_UNIT = 100;
    public static final int VIP_MULTIPLIER = 2;
    public static final long MIN_ACCRUAL_AMOUNT = 1_000;

    /**
     * 결제 금액 기준 적립 포인트.
     *
     * <p>소액 결제는 적립하지 않는다. 다만 GOLD 이상 등급은 이 하한을 면제받는다 — 등급 혜택이
     * 금액 조건보다 우선한다는 정책이다.
     */
    public int accrue(Customer customer, Money paidAmount) {
        boolean exemptFromMinimum = customer.member() && customer.grade().isAtLeast(Grade.GOLD);

        if (paidAmount.amount() < MIN_ACCRUAL_AMOUNT && !exemptFromMinimum) {
            return 0;
        }

        int points = (int) (paidAmount.amount() / POINT_UNIT);

        if (customer.isVip()) {
            points *= VIP_MULTIPLIER;
        }
        return points;
    }

    /**
     * 포인트 사용 가능 여부. 보유 포인트가 사용하려는 포인트 이상이어야 한다.
     *
     * @throws IllegalArgumentException 사용하려는 포인트가 1 미만일 때
     */
    public boolean canRedeem(int balance, int requested) {
        if (requested <= 0) {
            throw new IllegalArgumentException("사용할 포인트는 1 이상이어야 한다: " + requested);
        }
        return balance >= requested;
    }
}
