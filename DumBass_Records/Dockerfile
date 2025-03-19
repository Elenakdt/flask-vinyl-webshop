# syntax=docker/dockerfile:1
# Source: https://docs.docker.com/compose/gettingstarted/
FROM python:3.10-alpine
WORKDIR /app
ENV FLASK_APP=app.app
ENV FLASK_RUN_HOST=0.0.0.0
ENV PYTHONPATH=/app
RUN apk add --no-cache gcc musl-dev linux-headers mariadb-dev
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
EXPOSE 5000
COPY . .
CMD ["flask", "run", "--debug"]
