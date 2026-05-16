# Menggunakan base image Python yang ringan
FROM python:3.10-slim

# Menyiapkan folder kerja di dalam kontainer
WORKDIR /app

# Copy file requirements dan menginstal library
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Menjalankan Jupyter Lab saat kontainer menyala
CMD ["jupyter", "lab", "--ip='0.0.0.0'", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token='agriva'"]