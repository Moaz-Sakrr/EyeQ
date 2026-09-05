from fastapi import FastAPI

from .routers import alerts, history
from .ws import channel

app = FastAPI(title="EyeQ API", version="0.1.0")

app.include_router(alerts.router)
app.include_router(history.router)
app.include_router(channel.router)


@app.get("/health")
def health():
    return {"status": "ok", "contract": "0.1.0"}
