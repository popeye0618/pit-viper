package dev.pitviper.shop.web.dto;

import dev.pitviper.shop.domain.Grade;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

/**
 * 주문 견적 요청.
 *
 * @param customerId 고객 식별자
 * @param grade 회원 등급
 * @param member 회원 여부
 * @param unitPrice 단가
 * @param quantity 수량
 * @param island 도서산간 배송 여부
 */
public record QuoteRequest(
        @NotBlank String customerId,
        @NotNull Grade grade,
        boolean member,
        @Min(0) long unitPrice,
        @Min(1) int quantity,
        boolean island) {}
