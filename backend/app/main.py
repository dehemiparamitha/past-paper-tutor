from fastapi import FastAPI
from app.api.routes.chat import router as chat_router

app = FastAPI(
    title = "Past paper tutor API"
)

@app.get("/")
async def root():
    return {"message": "Welcome to the past paper tutor API"}

app.include_router(chat_router)