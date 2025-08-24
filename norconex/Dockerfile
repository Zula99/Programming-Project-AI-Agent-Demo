# Use OpenJDK 11 as the base image (Norconex requires Java)
FROM openjdk:11-jre-slim

# Set environment variables
ENV NORCONEX_HOME=/opt/norconex
ENV JAVA_OPTS="-Xms256m -Xmx1g"

# Install necessary packages
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create norconex user and directories
RUN useradd -r -m -s /bin/bash norconex && \
    mkdir -p ${NORCONEX_HOME} && \
    mkdir -p ${NORCONEX_HOME}/configs && \
    mkdir -p ${NORCONEX_HOME}/data && \
    mkdir -p ${NORCONEX_HOME}/logs

# Set working directory
WORKDIR ${NORCONEX_HOME}

# Copy all Norconex files from your local installation
COPY . ${NORCONEX_HOME}/

# Make shell scripts executable
RUN find ${NORCONEX_HOME} -name "*.sh" -exec chmod +x {} \;

# Set ownership of norconex directories
RUN chown -R norconex:norconex ${NORCONEX_HOME}

# Create wrapper scripts as root user (before switching to norconex user)
RUN echo '#!/bin/bash' > /usr/local/bin/norconex-crawler && \
    echo 'cd ${NORCONEX_HOME}' >> /usr/local/bin/norconex-crawler && \
    echo 'exec ./collector-http.sh "$@"' >> /usr/local/bin/norconex-crawler && \
    chmod +x /usr/local/bin/norconex-crawler

# Create health check script as root user
RUN echo '#!/bin/bash' > /usr/local/bin/health-check && \
    echo '# Simple health check - verify Java and Norconex installation' >> /usr/local/bin/health-check && \
    echo 'java -version && \' >> /usr/local/bin/health-check && \
    echo 'test -f ${NORCONEX_HOME}/collector-http.sh && \' >> /usr/local/bin/health-check && \
    echo 'echo "Norconex container is healthy"' >> /usr/local/bin/health-check && \
    chmod +x /usr/local/bin/health-check

# Switch to norconex user (do this AFTER creating scripts in /usr/local/bin)
USER norconex

# Expose volume mount points
VOLUME ["${NORCONEX_HOME}/data", "${NORCONEX_HOME}/configs"]

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD /usr/local/bin/health-check

# Default command - keep container running for exec commands from backend
CMD ["tail", "-f", "/dev/null"]