package com.pitviper.customer.entity;

import static org.assertj.core.api.Assertions.assertThat;

import com.pitviper.customer.enums.Grade;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("Customer")
class CustomerTest {

    @Test
    @DisplayName("VIP 등급 회원만 VIP 로 본다")
    void onlyVipGradeMemberIsVip() {
        assertThat(Customer.member("c1", Grade.VIP).isVip()).isTrue();
        assertThat(Customer.member("c2", Grade.GOLD).isVip()).isFalse();
    }

    @Test
    @DisplayName("비회원은 등급이 VIP 여도 VIP 가 아니다")
    void nonMemberIsNeverVip() {
        assertThat(new Customer("g1", Grade.VIP, false).isVip()).isFalse();
    }

    @Test
    @DisplayName("비회원은 BRONZE 등급의 비회원으로 만들어진다")
    void guestIsBronzeNonMember() {
        Customer guest = Customer.guest("g1");

        assertThat(guest.grade()).isEqualTo(Grade.BRONZE);
        assertThat(guest.member()).isFalse();
    }

    @Test
    @DisplayName("회원은 준 등급 그대로 회원으로 만들어진다")
    void memberKeepsGivenGrade() {
        Customer member = Customer.member("c1", Grade.SILVER);

        assertThat(member.grade()).isEqualTo(Grade.SILVER);
        assertThat(member.member()).isTrue();
    }
}
