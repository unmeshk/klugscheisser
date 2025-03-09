# Docker Setup for Klugbot

This document explains how to use Docker with the Klugbot application for both development and testing.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Setup

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/klugscheisser.git
cd klugscheisser
```

2. **Create environment file**

Copy the example environment file and update with your own values:

```bash
cp .env.example .env
```

Edit `.env` to add your Slack and Gemini API credentials.

## Running the Application

To start the application along with the PostgreSQL database:

```bash
docker-compose up --build app
```

This will:
- Build the Docker image for the application
- Start a PostgreSQL database container
- Start the Klugbot application
- Connect the two containers

Access the application at http://localhost:3000.

## Running Tests

To run the entire test suite:

```bash
./scripts/run_tests_docker.sh
```

To run a specific test file or directory:

```bash
./scripts/run_tests_docker.sh tests/unit/test_models.py
```

## Docker Services

The `docker-compose.yml` file defines the following services:

### app
The main application service that runs the Klugbot Slack bot.

### db
PostgreSQL database for production use.

### test
Test runner service that executes the test suite.

### db-test
Separate PostgreSQL database for testing purposes.

## Volumes

- `postgres_data`: Persists the production database data
- `postgres_test_data`: Persists the test database data
- `chroma_data`: Persists the ChromaDB vector database

## Customizing the Setup

### Database Configuration

Database settings are defined in `docker-compose.yml`. To modify:

```yaml
db:
  environment:
    - POSTGRES_USER=your_custom_user
    - POSTGRES_PASSWORD=your_custom_password
    - POSTGRES_DB=your_custom_db
```

Also update the `DATABASE_URL` in the app service accordingly.

### Application Port

To change the application port from the default 3000:

```yaml
app:
  ports:
    - "8080:3000"  # Map host port 8080 to container port 3000
```

## Development Workflow

For development, the source code directories are mounted as volumes, so changes to your code will be reflected in the container. The typical workflow is:

1. Make changes to the code
2. If needed, restart the container: `docker-compose restart app`
3. Run tests to verify changes: `./scripts/run_tests_docker.sh`

## Troubleshooting

### Database Connection Issues

If the application cannot connect to the database:

```bash
# Check if the database container is running
docker-compose ps

# View database logs
docker-compose logs db

# Check if the database is healthy
docker-compose exec db pg_isready -U klugbot
```

### Test Database Issues

If tests are failing with database errors:

```bash
# Rebuild the test database
docker-compose down -v
docker-compose up -d db-test
docker-compose run --rm test pytest -xvs tests/
```

### ChromaDB Issues

If vector search is not working:

```bash
# Check the ChromaDB volume
docker-compose exec app ls -la /app/src/chroma_storage

# Rebuild ChromaDB data directory
docker-compose down
docker volume rm klugscheisser_chroma_data
docker-compose up --build app
```