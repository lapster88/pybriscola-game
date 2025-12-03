FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

COPY . .

CMD ["python", "briscola_service.py"]
