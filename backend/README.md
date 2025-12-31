# Backend

This is the minimal backend for the enterprise ticketing system using FastAPI.

## Setup

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

3. Install dependencies:
   ```
   pip install -e .
   ```

4. To install dev dependencies (optional):
   ```
   pip install -e .[dev]
   ```

## Running the Server

Run the server with auto-reload:
```
uvicorn app.main:app --reload
```

The server will start at `http://localhost:8000`.

## Testing the Endpoint

Test the ping endpoint:
```
curl http://localhost:8000/ping
```

Or open in browser: `http://localhost:8000/ping`

Expected response: `{"status":"ok"}`
