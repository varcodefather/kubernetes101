FROM python:3.13-alpine
WORKDIR /app
COPY app.py backup.py restore.py ./
USER 1000
CMD ["python", "-u", "app.py"]
