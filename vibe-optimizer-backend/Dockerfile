# 1. Use an official Python image optimized for the M1 chip
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy the shopping list (requirements) first to save time
COPY requirements.txt .

# 4. Install the necessary Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your backend code (main.py, .env)
COPY . .

# 6. Start the FastAPI engine
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]