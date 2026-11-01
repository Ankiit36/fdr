# AICTE Security Deposit / FDR Management Portal

## Overview
The AICTE Security Deposit / FDR Management Portal is an enterprise web application designed to track, manage, and verify Fixed Deposit Receipts (FDRs) submitted by educational institutions. The platform facilitates end-to-end deposit lifecycles from submission and scrutiny to maturity tracking and renewals. It includes an automated review agent that extracts and checks deposit data against business rules and dispatches timely maturity notifications.

## Prerequisites
- **Python**: 3.12
- **Database**: SQLite (default for development), PostgreSQL (required for production only)

## Windows PowerShell Setup
Follow these steps in Windows PowerShell from the project root:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
```

## Getting Started (Commands in Order)
Run database migrations, seed initial demo data, and start the local development server:

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

## Key Portal URLs
- **Login**: [/accounts/login/](http://localhost:8000/accounts/login/)
- **Dashboard**: [/dashboard/](http://localhost:8000/dashboard/)
- **Institutions**: [/institutions/](http://localhost:8000/institutions/)
- **Deposits**: [/deposits/](http://localhost:8000/deposits/)
- **Agent Findings**: [/agent/findings/](http://localhost:8000/agent/findings/)
- **Notifications**: [/notifications/](http://localhost:8000/notifications/)
- **Audit Logs**: [/audit/](http://localhost:8000/audit/)
- **API Documentation (Swagger)**: [/api/docs/](http://localhost:8000/api/docs/)
- **Django Admin**: [/admin/](http://localhost:8000/admin/)

## Login Credentials
The `seed_demo` command creates the following user accounts with the default password `Demo@12345` (configurable via the `DEMO_PASSWORD` environment variable):

| Username | Role | Institution | Password |
| :--- | :--- | :--- | :--- |
| `admin_aicte` | ADMIN (Staff & Superuser) | None | `Demo@12345` |
| `officer_region1` | OFFICER | None | `Demo@12345` |
| `cit_user` | INSTITUTION | Chandigarh Institute of Technology (`CIT-CHD`) | `Demo@12345` |
| `rec_user` | INSTITUTION | Rajasthan Engineering College (`REC-JPR`) | `Demo@12345` |

## Run Tests
Run the automated test suite using pytest:

```powershell
pytest tests/
```

## Review Agent
Run the rule-based verification agent over all deposits:

```powershell
python manage.py run_agent_review
```

## Maturity Alerts
Process expiring/matured deposits and send in-app and email notifications:

```powershell
python manage.py send_maturity_alerts
```

## Scheduling
To ensure timely maturity reminders, schedule `send_maturity_alerts` to run once daily:

### Windows Task Scheduler
- **Action**: Start a program
- **Program/script**: Full absolute path to `.venv\Scripts\python.exe` (e.g. `C:\Users\<user>\Desktop\fdr_opencode\.venv\Scripts\python.exe`)
- **Add arguments**: `manage.py send_maturity_alerts`
- **Start in**: Absolute path to the project root folder (e.g. `C:\Users\<user>\Desktop\fdr_opencode`)
- **Trigger**: Daily at `09:00`

### Linux / macOS (Cron)
```cron
0 9 * * * cd /path/to/fdr_opencode && .venv/bin/python manage.py send_maturity_alerts
```

## Environment Variables
The application reads configuration values from environment variables defined in `.env` (sourced by `config/settings/base.py`, `config/settings/dev.py`, and `config/settings/prod.py`):

| Variable | Location | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `DJANGO_SETTINGS_MODULE` | Core | `config.settings.dev` | Django settings module (`config.settings.dev` or `config.settings.prod`) |
| `DJANGO_SECRET_KEY` | `base.py` | Dev fallback if DEBUG | Secret key used for cryptographic signing. Required in production. |
| `DJANGO_DEBUG` | `base.py`, `dev.py` | `"False"` (`base`), `"True"` (`dev`) | Enable or disable debug mode |
| `DJANGO_ALLOWED_HOSTS` | `base.py`, `dev.py`, `prod.py` | `"127.0.0.1,localhost"` (`dev`) | Comma-separated list of permitted hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `prod.py` | `""` | Comma-separated list of trusted CSRF origins (e.g. `https://*.onrender.com`) |
| `DATABASE_URL` | `base.py` | `""` (SQLite in dev) | Database connection URL (e.g. PostgreSQL on Render) |
| `EMAIL_BACKEND` | `base.py`, `dev.py`, `prod.py` | `"django.core.mail.backends.console.EmailBackend"` | Django email backend |
| `EMAIL_HOST` | `base.py`, `prod.py` | `""` (base), `"localhost"` (prod) | SMTP host |
| `EMAIL_PORT` | `base.py`, `prod.py` | `"587"` (base), `587` (prod) | SMTP port |
| `EMAIL_HOST_USER` | `base.py`, `prod.py` | `""` | SMTP username |
| `EMAIL_HOST_PASSWORD` | `base.py`, `prod.py` | `""` | SMTP password |
| `EMAIL_USE_TLS` | `base.py` | `"True"` | Use TLS for email |
| `DEFAULT_FROM_EMAIL` | `base.py`, `dev.py`, `prod.py` | `"noreply@fdr-portal.local"` (base), `"noreply@localhost"` (dev/prod) | Default sender email address |
| `REMINDER_WINDOW_DAYS` | `base.py` | `30` | Number of days before maturity to trigger EXPIRING reminders |
| `AWS_ACCESS_KEY_ID` | `base.py` | `""` | AWS S3 access key for django-storages |
| `AWS_SECRET_ACCESS_KEY` | `base.py` | `""` | AWS S3 secret access key |
| `AWS_STORAGE_BUCKET_NAME` | `base.py` | `""` | AWS S3 bucket name |
| `AWS_S3_REGION_NAME` | `base.py` | `"us-east-1"` | AWS S3 region |
| `MAX_DOCUMENT_SIZE_MB` | `base.py` | `5` | Maximum allowed document upload file size in megabytes |
| `AGENT_AMOUNT_TOLERANCE` | `base.py` | `"0"` | Allowed numeric tolerance when matching extracted amounts |
| `AGENT_HIGH_VALUE_AMOUNT` | `base.py` | `"1000000"` | Threshold above which deposits are prioritized as high value |
| `DEMO_PASSWORD` | `seed_demo.py` | `"Demo@12345"` | Initial password applied when creating seed demo users |

## Deployment Limitations
- **Uploaded Documents Persistence**: Render free web service has no persistent disk. Uploaded documents (PDFs) are stored on the ephemeral filesystem and will be lost on service restart or spin-down. S3 storage (via `django-storages` and AWS S3) is needed for durable production media storage.
- **Service Inactivity & Spin-down**: On Render's free tier, the web service spins down after 15 minutes of inactivity, resulting in a 50+ second delay (cold start) on the next incoming request.
- **Safe Seeding on Live Sites**: Demo data is not seeded automatically during build (`build.sh`) to prevent creating default demo passwords on public environments. To create demo users on the live site, run `python manage.py seed_demo` from Render's shell, ensuring `DEMO_PASSWORD` is set to a strong value first.

## Limitations
- **Bank Verification**: Bank confirmation is a mock implementation without direct core-banking or API links.
- **Email Delivery**: Emails are printed to the console in development via `ConsoleEmailBackend`. Production SMTP configuration requires valid SMTP server credentials.
- **Document Text Extraction**: Only digital PDFs with native text layers (via `pypdf`) are supported; there is no optical character recognition (OCR) for scanned images or rasterized PDFs.
