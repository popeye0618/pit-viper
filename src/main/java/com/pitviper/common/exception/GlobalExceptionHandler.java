package com.pitviper.common.exception;

import com.pitviper.common.response.FieldErrorResponse;
import com.pitviper.common.response.Response;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@Slf4j
@ControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<Response<Void>> handleBusinessException(BusinessException e) {
        log.warn("[BusinessException] code={}, detail={}", e.getErrorCode().getCode(), e.getMessage());

        return toResponseEntity(e.getErrorCode());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Response<List<FieldErrorResponse>>> handleMethodArgumentNotValidException(MethodArgumentNotValidException e) {
        List<FieldErrorResponse> errors = e.getBindingResult().getFieldErrors().stream()
                .map(ex -> new FieldErrorResponse(ex.getField(), ex.getDefaultMessage()))
                .toList();

        ErrorCode errorCode = GlobalErrorCode.VALIDATION_FAILED;
        return ResponseEntity.status(errorCode.getHttpStatus()).body(Response.error(errorCode, errors));
    }

    /**
     * 값 객체가 스스로를 지키려고 던지는 예외.
     *
     * <p>{@link BusinessException} 으로 감싸지 않은 이유는, 이 검증이 특정 업무 규칙이 아니라
     * 타입 자체의 불변식이기 때문이다. 서버 잘못이 아니므로 500 으로 새게 두지 않는다.
     */
    @ExceptionHandler({IllegalArgumentException.class, IllegalStateException.class})
    public ResponseEntity<Response<Void>> handleInvariantViolation(RuntimeException e) {
        log.warn("[InvariantViolation] detail={}", e.getMessage());

        return toResponseEntity(GlobalErrorCode.INVALID_INPUT_VALUE);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<Response<Void>> handleMethodArgumentTypeMismatchException(MethodArgumentTypeMismatchException e) {
        return toResponseEntity(GlobalErrorCode.TYPE_MISMATCH);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Response<Void>> handleHttpMessageNotReadableException(HttpMessageNotReadableException e) {
        return toResponseEntity(GlobalErrorCode.JSON_PARSE_ERROR);
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<Response<Void>> handleHttpRequestMethodNotSupportedException(HttpRequestMethodNotSupportedException e) {
        return toResponseEntity(GlobalErrorCode.METHOD_NOT_ALLOWED);
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<Response<Void>> handleNoResourceFoundException(NoResourceFoundException e) {
        return toResponseEntity(GlobalErrorCode.NOT_FOUND);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Response<Void>> handleUnexpected(Exception e) {
        log.error("[Exception] 예상하지 못한 서버 오류", e);

        return toResponseEntity(GlobalErrorCode.INTERNAL_SERVER_ERROR);
    }

    private static <T> ResponseEntity<Response<T>> toResponseEntity(ErrorCode errorCode) {
        return ResponseEntity.status(errorCode.getHttpStatus()).body(Response.error(errorCode));
    }
}
