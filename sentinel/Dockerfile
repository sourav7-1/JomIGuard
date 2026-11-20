FROM python:3.12-slim
WORKDIR /app
# rasterio's wheel needs libexpat, which slim images don't ship
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/*
# CPU-only torch keeps the image small; the U-Net is tiny (~1.9M params)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV HOST=0.0.0.0 PORT=5060
EXPOSE 5060
CMD ["python", "app.py"]
