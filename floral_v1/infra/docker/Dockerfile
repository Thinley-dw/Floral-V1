FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir .

EXPOSE 8050

CMD ["floral-dash", "--host", "0.0.0.0", "--port", "8050"]
