package com.mealmind.api;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.mealmind.api.PlanDtos.DayPlan;
import com.mealmind.api.PlanDtos.Meal;
import com.mealmind.api.PlanDtos.PlanResponse;
import com.mealmind.api.PlanDtos.WasteReport;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.reactive.function.client.WebClientRequestException;

/**
 * Slice test for the web layer: validation, happy path (AI client mocked), and
 * graceful degradation when the AI service is down. No real HTTP or Claude call.
 */
@WebMvcTest(PlanController.class)
class PlanControllerTest {

    @Autowired
    MockMvc mvc;

    @MockitoBean
    AiServiceClient aiService;

    private static final String VALID_BODY = """
        {
          "goal": "lose weight",
          "daily_calorie_target": 1800,
          "dietary_pattern": "vegetarian",
          "allergies": ["peanuts"],
          "pantry": [{"name": "rice", "expires_on": "2026-06-12"}],
          "days": 2
        }
        """;

    @Test
    void returnsPlanOnHappyPath() throws Exception {
        var response = new PlanResponse(
                List.of(new DayPlan("Monday",
                        List.of(new Meal("Rice bowl", 700, List.of("rice", "spinach"), List.of("rice"))),
                        700)),
                List.of("spinach"),
                new WasteReport(1, 1, 100, 1, 1, List.of()),
                "",
                1);
        when(aiService.generatePlan(any())).thenReturn(response);

        mvc.perform(post("/api/plan").contentType(MediaType.APPLICATION_JSON).content(VALID_BODY))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.days[0].day").value("Monday"))
                .andExpect(jsonPath("$.waste_report.pantry_utilization_pct").value(100))
                .andExpect(jsonPath("$.grocery_list[0]").value("spinach"));
    }

    @Test
    void rejectsMissingCalorieTargetWith400() throws Exception {
        mvc.perform(post("/api/plan")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"goal\": \"bulk up\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("validation_failed"));
    }

    @Test
    void returns503WhenAiServiceUnreachable() throws Exception {
        when(aiService.generatePlan(any()))
                .thenThrow(new WebClientRequestException(
                        new RuntimeException("connection refused"),
                        org.springframework.http.HttpMethod.POST,
                        java.net.URI.create("http://ai-service:8000/agent/plan"),
                        new org.springframework.http.HttpHeaders()));

        mvc.perform(post("/api/plan").contentType(MediaType.APPLICATION_JSON).content(VALID_BODY))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.error").value("ai_service_unavailable"));
    }
}
