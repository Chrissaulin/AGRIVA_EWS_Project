FROM python:3.9-slim

# Atur working directory di dalam container
WORKDIR /app

# Salin requirements.txt dan instal paket library
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode backend
COPY . .

# Ekspos port 8000 untuk FastAPI
EXPOSE 8000

# Jalankan skrip seeder database terlebih dahulu sebelum mengaktifkan server FastAPI
# (Host 0.0.0.0 penting agar port container dapat diakses dari luar)
CMD ["sh", "-c", "python scripts/seed_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
