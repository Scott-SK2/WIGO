# syntax=docker/dockerfile:1.7
FROM python:3.13-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=wigo.settings.prod

# GeoDjango : GDAL, GEOS, PROJ ; client PostgreSQL pour les scripts de sauvegarde
RUN apt-get update && apt-get install -y --no-install-recommends \
      binutils libproj-dev gdal-bin libgdal32 libgeos-c1v5 postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

COPY . .
RUN addgroup --system wigo && adduser --system --ingroup wigo wigo \
    && mkdir -p /app/media /app/staticfiles && chown -R wigo:wigo /app
USER wigo

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://localhost:8000/health/ || exit 1
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn wigo.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-3} --timeout 60 --access-logfile -"]
