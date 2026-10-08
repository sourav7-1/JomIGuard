from fastapi import FastAPI

app = FastAPI(title="JomiGuard API")

@app.get("/health")
def health():
    return {"status": "ok"}
