# Build stage: compile and test with Maven
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src ./src
RUN mvn -B -q package

# Runtime stage: small JRE image with just the jar
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /build/target/publisher.jar .
CMD ["java", "-jar", "publisher.jar"]
