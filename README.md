# Training App

Full-stack training application demonstrating: Django web application, user authentication, training plan generation, machine learning algorithms, data analysis, SQLite database, Nginx reverse proxy, Docker & Docker Compose, environment variables (.env), static files handling, and CI with GitHub Actions.

Architecture:

User > Nginx > Django/Gunicorn > SQLite

Main features:

- user registration and login
- user dashboard
- biometric data and training preferences
- training plan generation
- training calendar
- workout details
- progress tracking
- goals, rewards and notifications
- data analysis for weight, hydration and calories
- machine learning models for workout recommendations and predictions
- optional fitness chat using OpenAI API

Technologies:

- Python
- Django
- SQLite
- pandas
- numpy
- scikit-learn
- joblib
- Gunicorn
- Nginx
- Docker
- Docker Compose
- GitHub Actions

Run project:

```bash
docker compose up --build
```

Application is available at:

```text
http://localhost
```

Environment variables:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
OPENAI_API_KEY=
```

This project includes a CI pipeline using GitHub Actions that:

- installs Python dependencies
- runs Django system checks
- runs Django tests
- builds Docker image



[![CI](https://github.com/kawkaAW/Trenning-app/actions/workflows/ci.yml/badge.svg)](https://github.com/kawkaAW/Trenning-app/actions/workflows/ci.yml)
