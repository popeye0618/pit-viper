package com.pitviper.customer.entity;

import com.pitviper.customer.enums.Grade;

/**
 * 주문하는 고객.
 *
 * <p>비회원도 주문할 수 있지만 등급 혜택은 받지 못한다. 그래서 등급과 회원 여부를 따로 들고 있고,
 * 혜택 판정은 반드시 두 값을 함께 본다.
 *
 * @param id 고객 식별자
 * @param grade 회원 등급 (비회원이면 의미 없음)
 * @param member 회원 여부
 */
public record Customer(String id, Grade grade, boolean member) {

    public static Customer guest(String id) {
        return new Customer(id, Grade.BRONZE, false);
    }

    public static Customer member(String id, Grade grade) {
        return new Customer(id, grade, true);
    }

    public boolean isVip() {
        return member && grade == Grade.VIP;
    }
}
