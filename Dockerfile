FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501

WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
COPY app.py ./app.py
COPY src ./src

RUN pip install --upgrade pip && pip install -r requirements.txt && pip install -e .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
