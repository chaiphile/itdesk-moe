FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Place package files under /app/ai_gateway so `import ai_gateway` works inside the container
RUN mkdir -p /app/ai_gateway
COPY . /app/ai_gateway
ENV PYTHONPATH=/app
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "ai_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
