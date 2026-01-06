from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scraper import scrape_seace_top_5_paginado
import uvicorn
import os

app = FastAPI()

# Configuración de CORS (Permite que cualquier web pida datos)
# En producción estricta, cambiarías "*" por el dominio de tu landing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "ok", "message": "API de Licitaciones BDI funcionando"}

@app.get("/api/licitaciones")
async def get_licitaciones():
    # Llamamos a tu función scraper
    data = await scrape_seace_top_5_paginado()
    return data

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)