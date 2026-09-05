FROM python:3.11-slim
WORKDIR /app
COPY services/cv-engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY contracts /contracts
COPY services/cv-engine/src /app/src
ENV PYTHONPATH=/app/src:/contracts
CMD ["python", "-c", "from eyeq_cv.pipeline import Pipeline; p=Pipeline(); print(len(p.process_frame()), 'seats scored')"]
