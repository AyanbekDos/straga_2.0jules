from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Импорт роутеров
from api.routes import datasets

app = FastAPI(title="CCE API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(datasets.router)

@app.get("/")
async def root():
    return {"message": "CCE API работает"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)