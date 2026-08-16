package dev.pitviper.shop.web;

import dev.pitviper.shop.domain.Customer;
import dev.pitviper.shop.domain.Money;
import dev.pitviper.shop.service.OrderService;
import dev.pitviper.shop.web.dto.QuoteRequest;
import dev.pitviper.shop.web.dto.QuoteResponse;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 주문 견적 API.
 *
 * <p>계산 규칙은 전부 도메인·서비스에 있고 여기는 변환만 한다. 컨트롤러에 규칙이 새면 테스트가
 * HTTP 를 거쳐야만 가능해진다.
 */
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @PostMapping("/quote")
    public QuoteResponse quote(@Valid @RequestBody QuoteRequest request) {
        Customer customer =
                request.member()
                        ? Customer.member(request.customerId(), request.grade())
                        : Customer.guest(request.customerId());
        Money unitPrice = Money.of(request.unitPrice());

        Money finalPrice =
                orderService.finalPrice(customer, unitPrice, request.quantity(), request.island());
        int points =
                orderService.pointsFor(customer, unitPrice, request.quantity(), request.island());

        return new QuoteResponse(finalPrice.amount(), points);
    }

    /** 도메인이 던지는 규칙 위반은 400 으로 돌려준다. 서버 잘못이 아니라 요청 잘못이다. */
    @ExceptionHandler({IllegalArgumentException.class, IllegalStateException.class})
    public ResponseEntity<String> handleRuleViolation(RuntimeException e) {
        return ResponseEntity.badRequest().body(e.getMessage());
    }
}
