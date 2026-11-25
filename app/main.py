from fastapi import FastAPI

app = FastAPI(title="Suspicious Login Detection API")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
