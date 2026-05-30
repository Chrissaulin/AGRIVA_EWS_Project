FROM node:18-slim

# Atur working directory di dalam container
WORKDIR /app

# Salin package.json dan instal dependensi modul
COPY package.json .
RUN npm install

# Salin seluruh kode frontend
COPY . .

# Ekspos port 5173 untuk Vite dev server
EXPOSE 5173

# Jalankan dev server Vite
CMD ["npm", "run", "dev"]
