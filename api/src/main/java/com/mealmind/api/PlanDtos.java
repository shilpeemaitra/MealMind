package com.mealmind.api;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;

/**
 * Data transfer objects shared across the API. These mirror the Pydantic models in
 * the Python AI service (ai-service/app/schemas.py) — keep the two in sync.
 *
 * <p>Java records give us immutable, boilerplate-free DTOs that Jackson serializes
 * to/from JSON automatically.
 */
public final class PlanDtos {

    private PlanDtos() {}

    /** Incoming request from the React frontend. */
    public record PlanRequest(
            @NotBlank String goal,
            @Min(1) @NotNull Integer dailyCalorieTarget,
            String dietaryPattern,
            List<String> allergies,
            List<String> pantry,
            Integer days
    ) {}

    public record Meal(String name, int calories, List<String> ingredients) {}

    public record DayPlan(String day, List<Meal> meals, int totalCalories) {}

    /** Final response, assembled by the agent and passed straight through. */
    public record PlanResponse(
            List<DayPlan> days,
            List<String> groceryList,
            String notes,
            int revisions
    ) {}
}
