package com.mealmind.api;

import com.fasterxml.jackson.annotation.JsonFormat;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.LocalDate;
import java.util.List;

/**
 * Data transfer objects shared across the API. These mirror the Pydantic models in
 * the Python AI service (ai-service/app/schemas.py) — keep the two in sync.
 *
 * <p>Java records give us immutable, boilerplate-free DTOs that Jackson serializes
 * to/from JSON automatically. The global SNAKE_CASE naming strategy (application.yml)
 * maps e.g. {@code dailyCalorieTarget} ⇄ {@code daily_calorie_target}.
 */
public final class PlanDtos {

    private PlanDtos() {}

    /** An ingredient the user already has, with optional expiry. */
    public record PantryItem(
            @NotBlank String name,
            String quantity,
            @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd")
            LocalDate expiresOn
    ) {}

    /** Incoming request from the React frontend. */
    public record PlanRequest(
            @NotBlank String goal,
            @Min(800) @Max(6000) @NotNull Integer dailyCalorieTarget,
            String dietaryPattern,
            List<String> allergies,
            @Valid List<PantryItem> pantry,
            @Min(1) @Max(7) Integer days
    ) {}

    public record Meal(String name, int calories, List<String> ingredients, List<String> usesPantry) {}

    public record DayPlan(String day, List<Meal> meals, int totalCalories) {}

    /** The signature 'use it up' metrics. */
    public record WasteReport(
            int pantryItemsTotal,
            int pantryItemsUsed,
            int pantryUtilizationPct,
            int expiringSoonTotal,
            int expiringSoonUsed,
            List<String> unusedItems
    ) {}

    /** Final response, assembled by the agent and passed straight through. */
    public record PlanResponse(
            List<DayPlan> days,
            List<String> groceryList,
            WasteReport wasteReport,
            String notes,
            int revisions
    ) {}
}
