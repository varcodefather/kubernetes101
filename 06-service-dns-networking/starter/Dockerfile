FROM python:3.13-alpine
RUN apk add --no-cache bind-tools
WORKDIR /app
COPY app.py .
USER 65532
CMD ["python", "-u", "app.py"]
