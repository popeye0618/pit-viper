package com.pitviper.common.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.pitviper.common.exception.ErrorCode;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record Response<T>(
        String code,
        int status,
        String message,
        T data
) {

    private static final String OK_CODE = "GEN-000";
    private static final int OK_STATUS = 200;

    public static Response<Void> ok() {
        return new Response<>(OK_CODE, OK_STATUS, null, null);
    }

    public static <T> Response<T> ok(T data) {
        return new Response<>(OK_CODE, OK_STATUS, null, data);
    }

    public static <T> Response<T> error(ErrorCode errorCode) {
        return new Response<>(errorCode.getCode(), errorCode.getHttpStatus().value(), errorCode.getMessage(), null);
    }

    public static <T> Response<T> error(ErrorCode errorCode, T data) {
        return new Response<>(errorCode.getCode(), errorCode.getHttpStatus().value(), errorCode.getMessage(), data);
    }
}
