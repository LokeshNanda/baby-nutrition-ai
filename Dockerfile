# Baby Nutrition AI - production-ready image
FROM python:3.12-slim

WORKDIR /app

# Install package and dependencies
COPY pyproject.toml .
COPY src/ src/
COPY config/ config/

RUN pip install --no-cache-dir -e .

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "baby_nutrition_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]
