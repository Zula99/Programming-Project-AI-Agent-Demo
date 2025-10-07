# Use OpenJDK 17 as base image
FROM openjdk:17-jdk-slim

# Set working directory
WORKDIR /app

# Install Maven
RUN apt-get update && \
    apt-get install -y maven && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . /app

# Build the application
RUN mvn clean package -DskipTests

# Create directories for configuration and data
RUN mkdir -p /opt/norconex/configs /opt/norconex/data /opt/norconex/logs

# Set environment variables
ENV JAVA_OPTS="-Xmx2g -Xms512m"

# Copy the built JAR to a predictable location
RUN cp runner/target/runner-*-SNAPSHOT.jar /app/norconex-runner.jar

# Create a simple health check script
RUN echo '#!/bin/bash\necho "Norconex Runner is ready"\nexit 0' > /usr/local/bin/health-check && \
    chmod +x /usr/local/bin/health-check

# Copy and setup the trigger crawler script
COPY trigger-crawler.sh /app/trigger-crawler.sh
RUN chmod +x /app/trigger-crawler.sh

# Default command - run the trigger crawler monitoring script
CMD ["/app/trigger-crawler.sh"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/health-check