package com.pitviper.customer.enums;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("Grade")
class GradeTest {

    @Test
    @DisplayName("같은 등급도 이상으로 본다")
    void treatsSameGradeAsAtLeast() {
        assertThat(Grade.GOLD.isAtLeast(Grade.GOLD)).isTrue();
    }

    @Test
    @DisplayName("서열이 높으면 이상이고 낮으면 미만이다")
    void comparesByRank() {
        assertThat(Grade.VIP.isAtLeast(Grade.BRONZE)).isTrue();
        assertThat(Grade.SILVER.isAtLeast(Grade.GOLD)).isFalse();
    }

    @Test
    @DisplayName("등급 서열은 BRONZE·SILVER·GOLD·VIP 순이다")
    void pinsRankOrder() {
        // isAtLeast 가 선언 순서를 서열로 쓴다. 순서가 바뀌면 비교의 의미가 조용히 달라진다.
        assertThat(Grade.values())
                .containsExactly(Grade.BRONZE, Grade.SILVER, Grade.GOLD, Grade.VIP);
    }

    @Test
    @DisplayName("등급별 보너스 할인율이 정책값대로 꽂혀 있다")
    void pinsBonusRates() {
        // 상수에 꽂힌 데이터에는 뮤테이션 신호가 닿지 않는다 — 값을 직접 고정해 둔다.
        assertThat(Grade.BRONZE.getBonusRate()).isEqualTo(0.0);
        assertThat(Grade.SILVER.getBonusRate()).isEqualTo(0.05);
        assertThat(Grade.GOLD.getBonusRate()).isEqualTo(0.10);
        assertThat(Grade.VIP.getBonusRate()).isEqualTo(0.20);
    }
}
