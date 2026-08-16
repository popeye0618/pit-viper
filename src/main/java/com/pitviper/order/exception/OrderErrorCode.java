package com.pitviper.order.exception;

import com.pitviper.common.exception.ErrorCode;
import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@RequiredArgsConstructor
public enum OrderErrorCode implements ErrorCode {

    INVALID_QUANTITY("ORDER-001", HttpStatus.BAD_REQUEST, "Order quantity must be at least 1."),
    QUANTITY_LIMIT_EXCEEDED("ORDER-002", HttpStatus.BAD_REQUEST, "Order quantity exceeds the per-order limit."),
    INVALID_POINT_AMOUNT("ORDER-011", HttpStatus.BAD_REQUEST, "Points to redeem must be at least 1.");

    private final String code;
    private final HttpStatus httpStatus;
    private final String message;
}
