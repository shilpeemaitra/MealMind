package com.mealmind.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;
import org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration;

/**
 * Entry point for the MealMind Spring Boot API.
 *
 * <p>Datasource/JPA auto-configuration is excluded for now so the app boots without
 * a running Postgres (we have no entities until Week 3). When you add the first
 * {@code @Entity}, remove these two excludes to turn persistence back on.
 */
@SpringBootApplication(exclude = {
        DataSourceAutoConfiguration.class,
        HibernateJpaAutoConfiguration.class
})
public class MealMindApplication {

    public static void main(String[] args) {
        SpringApplication.run(MealMindApplication.class, args);
    }
}
