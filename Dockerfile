FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt
COPY src/ src/
COPY models/modele_final.joblib models/modele_final.joblib
ENV PYTHONPATH=/app/src
EXPOSE 8000
CMD ["uvicorn", "fraude_mobile_money.api:app", "--host", "0.0.0.0", "--port", "8000"]
