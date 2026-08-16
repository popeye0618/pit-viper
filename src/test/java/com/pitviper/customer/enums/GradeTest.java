package com.pitviper.customer.enums;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("Grade")
class GradeTest {

    @Test
    void 같은_등급도_이상으로_본다() {
        assertThat(Grade.GOLD.isAtLeast(Grade.GOLD)).isTrue();
    }

    @Test
    void 높은_등급은_낮은_등급_이상이다() {
        assertThat(Grade.VIP.isAtLeast(Grade.BRONZE)).isTrue();
    }

    @Test
    void 낮은_등급은_높은_등급_이상이_아니다() {
        assertThat(Grade.SILVER.isAtLeast(Grade.GOLD)).isFalse();
    }

    @Test
    void 등급마다_보너스_할인율이_다르다() {
        assertThat(Grade.BRONZE.getBonusRate()).isEqualTo(0.0);
        assertThat(Grade.SILVER.getBonusRate()).isEqualTo(0.05);
        assertThat(Grade.GOLD.getBonusRate()).isEqualTo(0.10);
        assertThat(Grade.VIP.getBonusRate()).isEqualTo(0.20);
    }
}
