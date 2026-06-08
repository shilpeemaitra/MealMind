package com.mealmind.api;

import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.reactive.function.client.WebClientResponseException;

/**
 * Translates exceptions into clean JSON error responses so the frontend never
 * sees a raw stack trace. Three cases worth distinguishing for the user:
 *   - bad input            → 400 with field-level messages
 *   - AI service unreachable/slow → 503 (it's a dependency problem, not theirs)
 *   - AI service returned an error → propagate a sensible status
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    public record ApiError(String error, Object detail) {}

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiError> handleValidation(MethodArgumentNotValidException ex) {
        Map<String, String> fields = ex.getBindingResult().getFieldErrors().stream()
                .collect(Collectors.toMap(
                        f -> f.getField(),
                        f -> f.getDefaultMessage() == null ? "invalid" : f.getDefaultMessage(),
                        (a, b) -> a));
        return ResponseEntity.badRequest().body(new ApiError("validation_failed", fields));
    }

    /** AI service unreachable, DNS failure, or response timeout. */
    @ExceptionHandler(WebClientRequestException.class)
    public ResponseEntity<ApiError> handleAiDown(WebClientRequestException ex) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(new ApiError("ai_service_unavailable",
                        "The meal-planning agent is temporarily unreachable. Please try again."));
    }

    /** AI service returned a non-2xx response. */
    @ExceptionHandler(WebClientResponseException.class)
    public ResponseEntity<ApiError> handleAiError(WebClientResponseException ex) {
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                .body(new ApiError("ai_service_error", ex.getStatusText()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiError> handleGeneric(Exception ex) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new ApiError("internal_error", "Something went wrong."));
    }
}
