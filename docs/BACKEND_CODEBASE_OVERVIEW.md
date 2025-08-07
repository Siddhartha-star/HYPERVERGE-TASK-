# Backend Codebase Overview

This document provides an overview of the backend codebase, its functionalities, and essential details for modification.

## 1. Project Structure
The `src/api` directory is the core of the backend application. It contains the following key directories and files:

- **`db/`**: Handles all database interactions, including models and CRUD operations for various entities like users, courses, tasks, etc.
- **`routes/`**: Defines all the API endpoints and their respective handlers. Each file typically corresponds to a major resource or functional area (e.g., `auth.py`, `user.py`, `course.py`).
- **`utils/`**: Contains various utility functions and helper modules used across the application, such as `audio.py`, `concurrency.py`, `s3.py`, and `logging.py`.
- **`__pycache__/`**: Python bytecode cache.
- **`config.py`**: Configuration settings for the application.
- **`cron.py`**: Defines scheduled tasks and cron jobs.
- **`llm.py`**: Logic related to Large Language Model (LLM) interactions.
- **`main.py`**: The main entry point of the FastAPI application.
- **`models.py`**: Defines Pydantic models for request and response data validation and serialization.
- **`public.py`**: Contains publicly accessible API endpoints, often without authentication.
- **`scheduler.py`**: Manages the scheduling of background tasks.
- **`settings.py`**: Application settings and environment variables.
- **`slack.py`**: Integrations with Slack for notifications or other functionalities.
- **`todo`**: A file likely containing temporary to-do notes.
- **`websockets.py`**: Handles WebSocket connections and real-time communication.

## 2. Core Functionalities
The backend application, built with FastAPI, provides a range of functionalities including:

- **Application Lifespan Management**: Handles startup procedures such as initializing the scheduler, ensuring the upload directory exists, and resuming any pending AI-driven task or course structure generation jobs. It also gracefully shuts down the scheduler.
- **Error Monitoring**: Integrates with Bugsnag to monitor and report application errors, providing insights into issues and facilitating debugging.
- **CORS Configuration**: Implements Cross-Origin Resource Sharing (CORS) middleware to allow secure communication between the frontend and backend, crucial for web applications deployed on different domains.
- **Static File Serving**: Serves static files, specifically user-uploaded content, from a designated local directory, making them accessible via a defined URL path.
- **Health Check**: Exposes a simple `/health` endpoint that returns an "ok" status, used for liveness and readiness probes in deployment environments.
- **Asynchronous Operations**: Leverages Python's `asyncio` for non-blocking execution of long-running tasks, particularly for resuming AI generation processes, enhancing application responsiveness.

## 3. API Endpoints
API routes are modularized, with each major functional area having its dedicated router, improving organization and maintainability. The main API groups and their prefixes are:

- **`/file`**: For handling file uploads and downloads.
- **`/ai`**: Dedicated to Artificial Intelligence functionalities, including task and course structure generation.
- **`/auth`**: Manages user authentication and authorization processes.
- **`/tasks`**: Provides endpoints for managing learning tasks.
- **`/chat`**: Handles chat-related functionalities.
- **`/users`**: Manages user profiles and related operations.
- **`/organizations`**: For managing organizational data.
- **`/cohorts`**: Manages cohorts or groups of users.
- **`/courses`**: Provides functionalities for managing educational courses.
- **`/milestones`**: Manages project milestones or learning progress.
- **`/scorecards`**: For functionalities related to scorecards or evaluations.
- **`/code`**: Handles code-related operations.
- **`/hva`**: Functionalities related to Human Value Alignment (HVA).
- **`/ws`**: Manages WebSocket connections for real-time communication.

## 4. Database Schema and Interactions
The backend primarily utilizes a SQLite database, with the schema defined and initialized in `src/api/db/__init__.py`. The database interactions are asynchronous, leveraging `asyncio` for non-blocking operations.

### Key Tables and Their Relationships:

- **`organizations`**: Stores organizational details (slug, name, logo, OpenAI API key). Organizations can have multiple API keys.
- **`org_api_keys`**: Manages API keys linked to `organizations`.
- **`users`**: Contains user profiles (email, names, display picture color). Users can belong to multiple organizations and cohorts.
- **`user_organizations`**: A many-to-many relationship table linking `users` to `organizations` with a defined `role`.
- **`cohorts`**: Defines groups within an organization. Cohorts are linked to `organizations`.
- **`user_cohorts`**: Links `users` to `cohorts` with a specified `role` and `joined_at` timestamp.
- **`courses`**: Stores details about educational courses. Courses are linked to `organizations`.
- **`course_cohorts`**: Links `courses` to `cohorts`, including drip content settings (e.g., `is_drip_enabled`, `frequency_value`, `frequency_unit`, `publish_at`).
- **`milestones`**: Defines milestones, linked to `organizations`.
- **`course_milestones`**: Links `courses` to `milestones` with an `ordering`.
- **`tasks`**: Stores learning tasks (type, content blocks, title, status, scheduled publish time). Tasks are linked to `organizations`.
- **`course_tasks`**: Links `tasks` to `courses` and can also be associated with `milestones`.
- **`questions`**: Contains questions associated with `tasks` (type, content blocks, answer, input type, coding language, generation model, response type, position, feedback visibility, context, title).
- **`scorecards`**: Defines criteria for evaluations.
- **`question_scorecards`**: Links `questions` to `scorecards`.
- **`chat_history`**: Stores chat logs between users and `questions` (user, question, role, content, response type).
- **`task_completions`**: Tracks the completion status of `tasks` and `questions` by `users`.
- **`course_generation_jobs`**: Records jobs related to AI-driven `course` generation.
- **`task_generation_jobs`**: Records jobs related to AI-driven `task` generation.
- **`code_drafts`**: Stores `user`'s code drafts for specific `questions`.

### Database Initialization and Migration:

The `init_db()` function in `src/api/db/__init__.py` is responsible for:
- Ensuring the database directory exists.
- Creating all necessary tables if they do not already exist.
- Applying default settings to the database on its first creation (`set_db_defaults`).

The `delete_useless_tables()` function and the `ALTER TABLE` statements within `init_db()` (and potentially `migration.py`) indicate a mechanism for database schema evolution, handling additions of new columns and dropping deprecated tables, ensuring the database schema stays up-to-date with application changes.

### Data Integrity and Performance:
- **Foreign Key Constraints**: Enforced across related tables to maintain data integrity.
- **Indexing**: Applied to frequently queried columns (e.g., foreign keys) to optimize read performance.

## 5. Authentication and Authorization

The backend implements an authentication and authorization mechanism primarily relying on **Google ID Tokens**.

### Authentication Flow:
1.  **Login/Signup**: Users authenticate by sending their Google ID token along with their email, given name, and family name to the `/auth/login` endpoint.
2.  **Token Verification**: The backend verifies the authenticity and validity of the Google ID token using Google's OAuth2 verification process and a configured `google_client_id`.
3.  **User Management**: Upon successful token verification, the system either registers a new user or retrieves an existing user's details from the database.

### Authorization:
While the `auth.py` primarily handles authentication, the database schema (as seen in `src/api/db/__init__.py`) and models (`src/api/models.py`) suggest a **Role-Based Access Control (RBAC)** system. Tables like `user_organizations` and `user_cohorts` include a `role` field, indicating that user permissions are likely managed based on their assigned roles within organizations and cohorts.

### Key Models:
- **`UserLoginData`**: (defined in `src/api/models.py`) Captures the necessary information for user login/signup via Google ID tokens.
- **`UserCourseRole`**: (defined in `src/api/models.py`) An Enum defining roles such as `ADMIN`, `LEARNER`, and `MENTOR`, which are likely used for authorization checks across different functionalities.

Further authorization logic would be distributed across various route handlers where specific resource access or actions are controlled based on the authenticated user's roles and permissions.

## 6. External Integrations
The backend integrates with several external services to extend its functionalities:

- **Slack**: Used for sending various notifications to predefined Slack channels. This includes alerts for new user sign-ups, users being added to cohorts or organizations, new organization and course creations, and periodic usage statistics reports (daily, monthly, yearly) detailing organizational and AI model usage. Webhook URLs are configured via application settings.
- **Amazon S3**: Utilized for scalable and secure file storage, particularly for user-uploaded media (e.g., audio files). The integration allows for:
    - Uploading files to specified S3 buckets with proper content types.
    - Downloading files from S3.
    - Generating unique S3 keys for file identification.
- **Google OAuth2**: (As detailed in Authentication and Authorization) Used for user authentication and identity verification through Google ID tokens.
- **Bugsnag**: (As detailed in Core Functionalities) An error monitoring and reporting service integrated to capture and track application errors.

## 7. Background Tasks and Scheduling
The backend utilizes `APScheduler` (specifically `AsyncIOScheduler`) for managing and executing background tasks and scheduled jobs. The scheduler is configured with the IST (Indian Standard Time) timezone.

### Scheduled Jobs:
- **Task Publishing**: A job runs every minute to check for and publish any tasks that have been scheduled for future release (`publish_scheduled_tasks` from `api.db.task`). This ensures that content becomes available to users at the intended time.
- **Daily Usage Statistics**: Every day at 9 AM IST, a job (`send_usage_summary_stats` from `api.cron`) gathers comprehensive usage statistics. This includes data on user messages and AI model usage, broken down by organization and time periods (last day, current month, current year). These statistics are then sent as notifications to a configured Slack channel, providing insights into platform activity and resource consumption.
- **Daily Traces Saving**: Another daily job, running at 10 AM IST (`save_daily_traces` from `api.utils.phoenix`), is responsible for collecting and storing application traces or logs. This data is crucial for observability, performance monitoring, and debugging.

## 8. Utilities
The `src/api/utils/` directory houses a collection of reusable utility functions and helper modules that support various aspects of the backend application:

- **`audio.py`**: (Minor module) Likely contains basic audio processing or handling utilities.
- **`concurrency.py`**: Provides tools for managing asynchronous operations efficiently, notably `async_batch_gather` for processing coroutines in batches to optimize resource usage and `async_index_wrapper` for preserving order in parallel processing.
- **`db.py`**: Encapsulates core database utility functions, including:
    - `get_new_db_connection()`: An asynchronous context manager for robust database connection management.
    - `set_db_defaults()`: Configures initial SQLite database settings, such as `journal_mode`.
    - `execute_db_operation()`, `execute_many_db_operation()`, `execute_multiple_db_operations()`: Generic functions for executing single, multiple, or batched SQL commands, providing flexible database interaction.
    - `check_table_exists()`: A helper for verifying the existence of database tables.
    - `serialise_list_to_str()` and `deserialise_list_from_str()`: Functions for converting list data to/from string format for storage in database columns.
- **`logging.py`**: Configures and provides a centralized logging mechanism for the application, outputting logs to a file (`app.log`) and potentially the console.
- **`phoenix.py`**: (As seen in `cron.py`) Likely deals with collecting and saving application traces/logs for observability and debugging purposes, possibly integrating with a tool like Phoenix.
- **`s3.py`**: (As detailed in External Integrations) Contains functions for interacting with Amazon S3 for file storage, including `upload_file_to_s3`, `download_file_from_s3_as_bytes`, and utilities for generating S3 keys.
- **`url.py`**: (Minor module) Likely contains utilities for URL manipulation or validation.

## 9. Testing
The backend includes a comprehensive test suite, primarily organized to mirror the application's module structure. This setup facilitates clear test ownership and easier navigation for developers.

### Framework and Tools:
- **Pytest**: The main testing framework used for running unit and integration tests.
- **`conftest.py`**: This file, located at the root of the `tests/` directory, is used for defining fixtures and hooks that can be shared across multiple test files. It likely contains setup and teardown logic for database connections, test clients (e.g., FastAPI's `TestClient`), and mock objects.

### Test Organization:
Tests are structured hierarchically within the `tests/` directory, following the `src/api/` structure:

- **`tests/api/`**: Contains tests for the core API components.
    - **`tests/api/db/`**: Houses tests specifically for database interaction modules (e.g., `test_user_db.py`, `test_course_db.py`), ensuring that data models and CRUD operations function correctly.
    - **`tests/api/routes/`**: Contains tests for the API endpoints defined in `src/api/routes/` (e.g., `test_auth.py`, `test_chat.py`, `test_course.py`). These tests typically focus on validating API request/response formats, status codes, and endpoint-specific logic.
    - **`tests/api/utils/`**: Includes tests for the utility functions found in `src/api/utils/`.
    - **`test_config.py`**: Tests related to application configuration settings.
    - **`test_cron.py`**: Tests for scheduled jobs and cron functionalities.
    - **`test_health_api.py`**: Basic tests for the health check endpoint.
    - **`test_llm.py`**: Tests for Large Language Model (LLM) related functionalities.
    - **`test_main.py`**: Tests for the main FastAPI application setup, including middleware and router inclusions.
    - **`test_models.py`**: Tests for Pydantic models, ensuring data validation and serialization work as expected.
    - **`test_public.py`**: Tests for publicly accessible API endpoints.
    - **`test_scheduler.py`**: Tests related to the `APScheduler` setup and job scheduling.
    - **`test_slack.py`**: Tests for Slack integration functionalities.
- **`tests/test_startup.py`**: Contains tests related to the application's startup process.

### How to Run Tests:
Tests can typically be run using the `pytest` command from the project root directory. Specific tests or directories can be targeted using `pytest <path_to_test_file_or_directory>`.

## 10. How to Modify the Codebase

This section provides guidelines for developers looking to modify, extend, or debug the backend codebase.

### Environment Setup:
1.  **Clone the Repository**: Ensure you have the project repository cloned locally.
2.  **Create a Virtual Environment**: It is highly recommended to use a Python virtual environment to manage dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
3.  **Install Dependencies**: Install the required Python packages listed in `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Environment Variables**: The application relies on environment variables for configuration (e.g., database paths, API keys, Slack webhooks). Refer to `api/settings.py` and `docs/ENV.md` (if available) for a complete list and their purposes. You'll typically need to create a `.env` file in the project root.

### Running the Application:
To run the FastAPI application, you can use Uvicorn:
```bash
uvicorn api.main:app --reload
```
This command will start the development server with auto-reloading enabled, which is useful for development.

### Adding New Features or Modifying Existing Ones:
1.  **API Endpoints**: When adding new API endpoints, define them within the appropriate router file in `src/api/routes/`. Ensure you define Pydantic models for request and response validation in `src/api/models.py`.
2.  **Database Interactions**: For new or modified database operations, create or update functions in the relevant file within `src/api/db/`. Utilize the `api.utils.db` functions (`get_new_db_connection`, `execute_db_operation`, etc.) for consistent and safe database interactions. Remember to add or update table creation logic in `src/api/db/__init__.py` if you introduce new tables or modify existing schemas.
3.  **Business Logic**: Place core business logic within the appropriate modules, typically called from API route handlers or scheduled tasks.
4.  **Utility Functions**: For common, reusable logic, consider adding it to an existing or new module within `src/api/utils/`.
5.  **LLM Interactions**: If your feature involves Large Language Model interactions, refer to `src/api/llm.py` and ensure proper integration and error handling.

### Testing:
- **Write Tests**: Always write unit and integration tests for new features and bug fixes. Place them in the corresponding `tests/` subdirectory mirroring the `src/api/` structure.
- **Run Tests**: Execute tests using `pytest` from the project root:
    ```bash
    pytest
    ```
    To run specific tests, provide the path to the test file or directory: `pytest tests/api/routes/test_your_new_feature.py`.
- **Fixtures**: Utilize shared fixtures defined in `tests/conftest.py` for common setup tasks.

### Debugging:
- **Logging**: Leverage the `api.utils.logging.logger` for structured logging. Configure log levels as needed in `api/settings.py`.
- **Error Monitoring**: For production environments, ensure Bugsnag is properly configured to capture and report errors.

### Code Style and Linting:
- Adhere to the existing code style. The project likely uses a linter and formatter (e.g., Black, Flake8). Ensure your IDE is configured to use them or run them manually before committing.

This document serves as a living guide and should be updated as the backend evolves.