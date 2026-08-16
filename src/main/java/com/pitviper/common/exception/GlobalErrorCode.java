package com.pitviper.common.exception;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@RequiredArgsConstructor
public enum GlobalErrorCode implements ErrorCode {

    // 400
    BAD_REQUEST("GEN-001", HttpStatus.BAD_REQUEST, "Bad request."),
    INVALID_INPUT_VALUE("GEN-002", HttpStatus.BAD_REQUEST, "Invalid input value."),
    VALIDATION_FAILED("GEN-003", HttpStatus.BAD_REQUEST, "Validation failed."),
    TYPE_MISMATCH("GEN-005", HttpStatus.BAD_REQUEST, "Type mismatch error."),
    JSON_PARSE_ERROR("GEN-006", HttpStatus.BAD_REQUEST, "Failed to parse JSON body."),

    // 404 / 405
    NOT_FOUND("GEN-031", HttpStatus.NOT_FOUND, "Resource not found."),
    METHOD_NOT_ALLOWED("GEN-041", HttpStatus.METHOD_NOT_ALLOWED, "Method not allowed."),

    // 500
    INTERNAL_SERVER_ERROR("GEN-091", HttpStatus.INTERNAL_SERVER_ERROR, "An internal server error occurred.");

    private final String code;
    private final HttpStatus httpStatus;
    private final String message;
}
