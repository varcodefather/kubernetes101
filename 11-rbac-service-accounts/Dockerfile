FROM python:3.13-alpine
WORKDIR /app
COPY api_check.py ./
USER 1000:1000
EXPOSE 8000
CMD ["python", "-u", "api_check.py"]
