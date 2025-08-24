# Norconex Runner

Maven multi-module project for executing Norconex web crawler operations with OpenSearch/Elasticsearch integration.

## Prerequisites

- Java 17 or higher
- Maven 3.9+ (or use included Maven wrapper)

## Project Structure

```
norconex-runner/
├── pom.xml                    # Parent POM
├── runner/                    # Main executable module
│   ├── pom.xml               # Runner module POM with shade plugin
│   └── src/main/java/
│       └── io/demo/nx/
│           └── Runner.java   # Main class entry point
├── mvnw / mvnw.cmd           # Maven wrapper scripts
└── .mvn/wrapper/             # Maven wrapper configuration
```

## Dependencies

- **com.norconex.collectors:norconex-collector-http:3.1.0**
- **com.norconex.collectors:norconex-collector-http-webdriver:3.1.0**
- **com.norconex.committers:norconex-committer-elasticsearch:3.1.0**
- **slf4j-api + logback-classic** (logging)
- **JUnit 5** (testing)

## Build Commands

### Using Maven Wrapper (Recommended)

```bash
# Clean and compile
./mvnw clean compile

# Run tests
./mvnw test

# Build fat JAR
./mvnw clean package

# Skip tests and build
./mvnw clean package -DskipTests
```

### Using System Maven

```bash
# Clean and compile
mvn clean compile

# Run tests
mvn test

# Build fat JAR
mvn clean package

# Skip tests and build
mvn clean package -DskipTests
```

## Run Commands

### After Building

```bash
# Run the fat JAR (from project root)
java -jar runner/target/runner-1.0.0-SNAPSHOT.jar

# Run with arguments
java -jar runner/target/runner-1.0.0-SNAPSHOT.jar arg1 arg2

# Run with JVM options
java -Xmx2g -jar runner/target/runner-1.0.0-SNAPSHOT.jar
```

### Using Maven Exec Plugin

```bash
# Run directly via Maven
./mvnw exec:java -Dexec.mainClass="io.demo.nx.Runner" -pl runner

# Run with arguments
./mvnw exec:java -Dexec.mainClass="io.demo.nx.Runner" -Dexec.args="arg1 arg2" -pl runner
```

## Output

The Runner currently parses command line arguments and prints "OK". Logs are written to:
- Console (INFO level)
- `logs/norconex-runner.log` (with rotation)

## Development

### Adding Norconex Functionality

The `Runner.java` class is ready to be extended with actual Norconex crawler operations:

```java
// Example: Load and execute crawler configuration
HttpCollector collector = new HttpCollector(collectorConfig);
collector.start();
```

### Configuration

- Logging configuration: `runner/src/main/resources/logback.xml`
- Maven dependencies: See parent and runner `pom.xml` files
- JVM settings: Can be added to `.mvn/jvm.config`

## Testing

```bash
# Run all tests
./mvnw test

# Run specific test class
./mvnw test -Dtest=RunnerTest
```

## Fat JAR Details

The Maven Shade Plugin creates a single executable JAR with:
- Main-Class: `io.demo.nx.Runner`
- All dependencies included
- Signed JARs cleaned (removes .SF, .DSA, .RSA files)
- Service discovery files merged