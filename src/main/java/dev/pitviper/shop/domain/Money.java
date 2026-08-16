package dev.pitviper.shop.domain;

/**
 * 금액을 나타내는 값 객체. 음수를 허용하지 않는다.
 *
 * <p>{@code long} 을 그대로 들고 다니지 않는 이유는, 금액에만 해당하는 규칙(음수 금지, 비율 적용 시
 * 반올림 방식)을 한곳에 모아두기 위해서다.
 */
public record Money(long amount) {

    public static final Money ZERO = new Money(0);

    /** record 의 compact constructor — 필드 대입은 자동으로 되고, 검증만 적는다. */
    public Money {
        if (amount < 0) {
            throw new IllegalArgumentException("금액은 음수일 수 없다: " + amount);
        }
    }

    public static Money of(long amount) {
        return new Money(amount);
    }

    public Money plus(Money other) {
        return new Money(amount + other.amount);
    }

    /**
     * 차감한 금액.
     *
     * @throws IllegalStateException 차감 결과가 음수가 될 때
     */
    public Money minus(Money other) {
        if (other.amount > amount) {
            throw new IllegalStateException("차감 결과가 음수가 된다: " + amount + " - " + other.amount);
        }
        return new Money(amount - other.amount);
    }

    public Money times(int quantity) {
        return new Money(amount * quantity);
    }

    /** 비율을 적용한 금액. 원 단위로 반올림한다. */
    public Money applyRate(double rate) {
        return new Money(Math.round(amount * rate));
    }

    public boolean isGreaterThan(Money other) {
        return amount > other.amount;
    }

    public boolean isZero() {
        return amount == 0;
    }
}
