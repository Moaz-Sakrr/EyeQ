FROM python:3.11-slim
WORKDIR /app
COPY services/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY contracts /contracts
COPY services/backend/src /app/src
ENV PYTHONPATH=/app/src:/contracts
EXPOSE 8000
CMD ["uvicorn", "eyeq_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
