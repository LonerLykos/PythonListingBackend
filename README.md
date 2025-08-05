# PythonRia

## Start

This is a backend multi-service project for managing a car listing platform. It is built using **Docker**, **FastAPI**, **Celery**, **Redis**, **RabbitMQ**, **MySQL**, and **MongoDB**.

### Requirements

Make sure the following tools are installed:
- **Docker**: Required for building and running containers.
- **Docker Compose**: Needed for defining and running multi-container Docker applications.
- **Bash terminal**: Required for running commands (e.g., Git Bash, Linux Terminal, or WSL).
- **Python**: Required for running project (recommended python version ">=3.12,<4.0")

### Project Startup

1. Clone the project from **GitHub**.
2. From the **project root directory**, run the following command in the Bash terminal to create `.env` files:
```bash
python script.py
```
3. Fill in all the required values inside the generated `.env` files.
4. Launch the project from the **project root directory** using:
```bash
bash start.sh
```

This script will automatically configure shared environment variables, build the services, and start the entire system.

---

## Tests

To run tests:

1. Make sure the project is fully up and running as described in the **Project Startup** section.
2. Then run tests for one or multiple services individually:

- **auth_service**:
```bash
docker compose exec auth poetry run pytest tests -v
```

- **listing_service**:
```bash
docker compose exec listing poetry run pytest tests -v
```

- **task_service**:
```bash
docker compose exec task poetry run pytest tests -v
```

To see more verbose logs during test execution, add the `-s` flag.

---

# *WARNING! THIS DATA MUST BE MOVED TO A SAFE LOCATION AND REMOVED FROM HERE!*

To create a SuperAdmin, run the following command:
```bash
docker compose exec auth poetry run python -m app.commands.create_superuser --email admin1@example.com --password P@ssW0rd --username Admin1 --user-id 1
```

Where:
- Replace `admin1@example.com` with your email
- Replace `P@ssW0rd` with your desired password
- Replace `Admin1` with your desired username
- `--user-id` must be a number between 1 and 5 (inclusive) and used only once; these IDs are reserved for platform owners.

---

## Application Features

This is a backend application for managing car sale listings.

### Auth Service

Provides:
- User registration
- Email-based password validation
- Login functionality
- Password reset via email

### Listing Service

Provides:
- Creation, update, and deletion of listings
- Submission of requests to admins for adding:
  - New car brands
  - Car models
  - Countries
  - Regions
  - Cities

### Task Service

Provides:
- Message queue processing
- Periodic tasks:
  - Currency exchange rate updates
  - Removal of expired tokens
  - Update of user premium status after expiration
- Telegram bot integration to help managers and admins perform moderation tasks