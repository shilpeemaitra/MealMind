package com.mealmind.api;

import com.mealmind.api.PlanDtos.PlanRequest;
import com.mealmind.api.PlanDtos.PlanResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Public API the React frontend calls. For now it simply orchestrates a call to
 * the AI agent service. In Week 3 this is where auth + persistence (saving plans
 * for a logged-in user) get layered in.
 *
 * <p>CORS is configured centrally in {@link WebConfig}, not here.
 */
@RestController
@RequestMapping("/api")
public class PlanController {

    private final AiServiceClient aiService;

    public PlanController(AiServiceClient aiService) {
        this.aiService = aiService;
    }

    @PostMapping("/plan")
    public PlanResponse plan(@Valid @RequestBody PlanRequest request) {
        return aiService.generatePlan(request);
    }
}
