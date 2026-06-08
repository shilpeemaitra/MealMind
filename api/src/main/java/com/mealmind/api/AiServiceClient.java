package com.mealmind.api;

import com.mealmind.api.PlanDtos.PlanRequest;
import com.mealmind.api.PlanDtos.PlanResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

/**
 * Thin client that calls the Python AI service (FastAPI + LangGraph) over HTTP.
 *
 * <p>The base URL comes from the AI_SERVICE_URL env var (see .env.example); in
 * docker-compose that resolves to the `ai-service` container.
 */
@Component
public class AiServiceClient {

    private final WebClient webClient;

    public AiServiceClient(@Value("${ai.service.url:http://localhost:8000}") String baseUrl) {
        this.webClient = WebClient.builder().baseUrl(baseUrl).build();
    }

    /** Forward a plan request to the agent and return its response. */
    public PlanResponse generatePlan(PlanRequest request) {
        return webClient.post()
                .uri("/agent/plan")
                .bodyValue(request)
                .retrieve()
                .bodyToMono(PlanResponse.class)
                .block();
    }
}
