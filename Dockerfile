FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY . .
RUN pip install --no-cache-dir --no-deps . && useradd --create-home openbil && mkdir -p /app/data && chown -R openbil:openbil /app
USER openbil
EXPOSE 8501
CMD ["python", "scripts/start_service.py"]
