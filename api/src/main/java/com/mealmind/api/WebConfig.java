package com.mealmind.api;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * CORS configuration driven by the WEB_CORS_ORIGIN env var (comma-separated list).
 *
 * <p>Locally that's the Vite dev server; in production it's your Vercel URL.
 * Centralizing it here (instead of @CrossOrigin on the controller) means one
 * place to manage allowed origins across all endpoints.
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final String[] allowedOrigins;

    public WebConfig(@Value("${web.cors.origin:http://localhost:5173}") String origins) {
        this.allowedOrigins = origins.split("\\s*,\\s*");
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins(allowedOrigins)
                .allowedMethods("GET", "POST", "OPTIONS")
                .allowedHeaders("*");
    }
}
