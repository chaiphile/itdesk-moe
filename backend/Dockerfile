FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
# Ensure boto3 is available in the runtime image for the scanner/service
RUN pip install --no-cache-dir boto3

COPY . .

# Copy entrypoint and make executable
COPY entrypoints/start.sh /start.sh
RUN sed -i 's/\r$//' /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
