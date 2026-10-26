FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home app && mkdir /data && chown app:app /data
COPY backend/app ./app
USER app
ENV DATABASE_URL=sqlite:////data/stock.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
