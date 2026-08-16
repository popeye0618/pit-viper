package dev.pitviper.shop.domain;

/** 회원 등급. 등급마다 추가 할인율을 가진다. */
public enum Grade {
    BRONZE(0.0),
    SILVER(0.05),
    GOLD(0.10),
    VIP(0.20);

    private final double bonusRate;

    Grade(double bonusRate) {
        this.bonusRate = bonusRate;
    }

    public double bonusRate() {
        return bonusRate;
    }

    /**
     * 이 등급이 {@code other} 이상인지.
     *
     * <p>선언 순서가 곧 등급 서열이라는 전제를 쓴다. 등급을 중간에 끼워 넣으면 이 비교가 조용히
     * 달라지므로, 새 등급은 서열에 맞는 위치에 넣어야 한다.
     */
    public boolean isAtLeast(Grade other) {
        return ordinal() >= other.ordinal();
    }
}
