package com.pitviper.order.dto;

/**
 * 주문 견적 응답.
 *
 * @param finalPrice 최종 결제 금액
 * @param earnedPoints 이 주문으로 적립될 포인트
 */
public record QuoteResponse(long finalPrice, int earnedPoints) {}
