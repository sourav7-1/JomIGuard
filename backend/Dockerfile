FROM python:3.12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-ben tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
# tessdata_best Bangla model in its own folder (apt pack stays); eng/osd linked so ben+eng works
ADD --checksum=sha256:1cd0129288d1f74f6661c35e638e487bd146a66bb732ecd9e011e48dcb0df623 \
    https://github.com/tesseract-ocr/tessdata_best/raw/4.1.0/ben.traineddata /usr/share/tessdata_best/
RUN ln -s /usr/share/tesseract-ocr/5/tessdata/eng.traineddata \
    /usr/share/tesseract-ocr/5/tessdata/osd.traineddata /usr/share/tessdata_best/
# best model is the default (data/preview/ocr/grid.md); the apt folder is still there
ENV TESSDATA_PREFIX=/usr/share/tessdata_best
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
