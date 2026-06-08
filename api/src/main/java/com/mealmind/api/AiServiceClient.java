package com.mealmind.api;

import com.mealmind.api.PlanDtos.PlanRequest;
import com.mealmind.api.PlanDtos.PlanResponse;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;

/**
 * Thin client that calls the Python AI service (FastAPI + LangGraph) over HTTP.
 *
 * <p>The base URL comes from the AI_SERVICE_URL env var (see .env.example); in
 * docker-compose that resolves to the {@code ai-service} container.
 *
 * <p>A generous timeout is set because the agent may re-plan several times
 * (each a Claude call). If it exceeds the budget, the call fails fast and the
 * global handler turns it into a clean 504 rather than hanging the request.
 */
@Component
public class AiServiceClient {

    // The agent can make up to MAX_REVISIONS LLM calls; give it real headroom.
    private static final Duration AGENT_TIMEOUT = Duration.ofSeconds(90);

    private final WebClient webClient;

    public AiServiceClient(@Value("${ai.service.url:http://localhost:8000}") String baseUrl) {
        HttpClient httpClient = HttpClient.create().responseTimeout(AGENT_TIMEOUT);
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .build();
    }

    /** Forward a plan request to the agent and return its response. */
    public PlanResponse generatePlan(PlanRequest request) {
        return webClient.post()
                .uri("/agent/plan")
                .bodyValue(request)
                .retrieve()
                .bodyToMono(PlanResponse.class)
                .block(AGENT_TIMEOUT);
    }
}
