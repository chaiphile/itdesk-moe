FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

# Copy entrypoint and make executable
COPY entrypoints/start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
