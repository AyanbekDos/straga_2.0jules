from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Импорт роутеров
from api.routes import users, auth, links, pages, chunks, embeddings, datasets

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
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(links.router, prefix="/api")
app.include_router(pages.router, prefix="/api")
app.include_router(chunks.router, prefix="/api")
app.include_router(embeddings.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "CCE API работает"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
