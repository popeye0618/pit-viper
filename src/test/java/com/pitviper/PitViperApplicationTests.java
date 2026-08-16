package com.pitviper;

import static org.assertj.core.api.Assertions.assertThat;

import com.pitviper.order.service.OrderService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * 스프링 컨텍스트가 뜨는지만 확인한다.
 *
 * <p>{@code integration} 태그를 붙인 이유는 pitest 가 이 테스트를 제외하게 하기 위해서다. 컨텍스트
 * 기동은 뮤턴트 하나당 수 초가 걸려 뮤테이션 분석 시간을 폭발시킨다.
 */
@SpringBootTest
@Tag("integration")
@DisplayName("애플리케이션 기동")
class PitViperApplicationTests {

    @Autowired private OrderService orderService;

    @Test
    @DisplayName("스프링 컨텍스트가 뜨고 서비스 빈이 주입된다")
    void loadsContext() {
        // 여기서는 isNotNull 이 맞다 — 계산이 없고, "빈이 존재하는가"가 곧 검증 대상이다.
        assertThat(orderService).isNotNull();
    }
}
