package com.pitviper.order.policy;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.pitviper.common.exception.BusinessException;
import com.pitviper.common.vo.Money;
import com.pitviper.customer.entity.Customer;
import com.pitviper.customer.enums.Grade;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

@DisplayName("PointPolicy")
class PointPolicyTest {

    private final PointPolicy policy = new PointPolicy();

    @Nested
    @DisplayName("적립")
    class AccrualTest {

        @Test
        @DisplayName("결제 금액을 적립 단위로 나눈 만큼 적립한다")
        void accruesByPointUnit() {
            assertThat(policy.accrue(Customer.member("c1", Grade.SILVER), Money.of(10_000)))
                    .isEqualTo(100);
        }

        @Test
        @DisplayName("적립 하한과 같으면 적립하고 1원 모자라면 적립하지 않는다")
        void accrualMinimumIsInclusive() {
            Customer silver = Customer.member("c1", Grade.SILVER);

            assertThat(policy.accrue(silver, Money.of(PointPolicy.MIN_ACCRUAL_AMOUNT)))
                    .isEqualTo(10);
            assertThat(policy.accrue(silver, Money.of(PointPolicy.MIN_ACCRUAL_AMOUNT - 1)))
                    .isZero();
        }

        @Test
        @DisplayName("GOLD 이상 회원은 하한 미만이어도 적립받는다")
        void goldAndAboveAreExemptFromMinimum() {
            assertThat(policy.accrue(Customer.member("c1", Grade.GOLD), Money.of(500)))
                    .isEqualTo(5);
        }

        @Test
        @DisplayName("GOLD 미만 회원과 비회원은 하한을 면제받지 못한다")
        void othersAreNotExemptFromMinimum() {
            assertThat(policy.accrue(Customer.member("c1", Grade.SILVER), Money.of(500)))
                    .isZero();
            assertThat(policy.accrue(new Customer("g1", Grade.GOLD, false), Money.of(500)))
                    .isZero();
        }

        @Test
        @DisplayName("VIP 회원은 적립 포인트가 배수로 늘어난다")
        void vipEarnsMultipliedPoints() {
            assertThat(policy.accrue(Customer.member("c1", Grade.VIP), Money.of(10_000)))
                    .isEqualTo(200);
        }
    }

    @Nested
    @DisplayName("사용")
    class RedemptionTest {

        @Test
        @DisplayName("보유 포인트가 사용 포인트와 같거나 많으면 쓸 수 있다")
        void allowsWhenBalanceCoversRequest() {
            assertThat(policy.canRedeem(1_000, 500)).isTrue();
            assertThat(policy.canRedeem(500, 500)).isTrue();
            assertThat(policy.canRedeem(499, 500)).isFalse();
        }

        @Test
        @DisplayName("사용 포인트가 1 미만이면 예외다")
        void rejectsNonPositiveRequest() {
            assertThatThrownBy(() -> policy.canRedeem(1_000, 0))
                    .isInstanceOf(BusinessException.class);
            assertThatThrownBy(() -> policy.canRedeem(1_000, -1))
                    .isInstanceOf(BusinessException.class);
        }

        @Test
        @DisplayName("사용 포인트 1은 합법이다")
        void acceptsSmallestRequest() {
            assertThat(policy.canRedeem(1, 1)).isTrue();
        }
    }

    @Test
    @DisplayName("적립 정책값이 정해진 대로 꽂혀 있다")
    void pinsPolicyConstants() {
        assertThat(PointPolicy.POINT_UNIT).isEqualTo(100);
        assertThat(PointPolicy.MIN_ACCRUAL_AMOUNT).isEqualTo(1_000);
        assertThat(PointPolicy.VIP_MULTIPLIER).isEqualTo(2);
    }
}
