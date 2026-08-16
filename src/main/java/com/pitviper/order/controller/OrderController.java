package com.pitviper.order.controller;

import com.pitviper.common.response.Response;
import com.pitviper.common.vo.Money;
import com.pitviper.customer.entity.Customer;
import com.pitviper.order.dto.QuoteRequest;
import com.pitviper.order.dto.QuoteResponse;
import com.pitviper.order.service.OrderService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 주문 견적 API.
 *
 * <p>계산 규칙은 전부 정책·서비스에 있고 여기는 변환만 한다. 컨트롤러에 규칙이 새면 테스트가
 * HTTP 를 거쳐야만 가능해진다.
 */
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/orders")
public class OrderController {

    private final OrderService orderService;

    @PostMapping("/quote")
    public Response<QuoteResponse> quote(@Valid @RequestBody QuoteRequest request) {
        Customer customer = request.member()
                ? Customer.member(request.customerId(), request.grade())
                : Customer.guest(request.customerId());
        Money unitPrice = Money.of(request.unitPrice());

        Money finalPrice = orderService.finalPrice(customer, unitPrice, request.quantity(), request.island());
        int points = orderService.pointsFor(customer, unitPrice, request.quantity(), request.island());

        return Response.ok(new QuoteResponse(finalPrice.amount(), points));
    }
}
