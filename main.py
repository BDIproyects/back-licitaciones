from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scraper import scrape_seace_top_5_paginado
import uvicorn
import os
import traceback

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATOS DE RESPALDO (Por si el scraper falla por memoria) ---
BACKUP_DATA = [
    {
        "id": 1,
        "nombre": "SERVICIO DE SEGURIDAD Y VIGILANCIA PARA LA SEDE CENTRAL - MODO RESPALDO",
        "tiempo": "Vence HOY",
        "link": "https://prod6.seace.gob.pe/buscador-publico/contrataciones/37505",
        "estado": "Vigente",
        "monto": "S/ 120,000"
    },
    {
        "id": 2,
        "nombre": "ADQUISICIÓN DE EQUIPOS DE CÓMPUTO DE ALTO RENDIMIENTO",
        "tiempo": "2 días restantes",
        "link": "https://prod6.seace.gob.pe/buscador-publico/contrataciones/37504",
        "estado": "Vigente",
        "monto": "S/ 45,000"
    },
    {
        "id": 3,
        "nombre": "CONTRATACIÓN DE SERVICIO DE MANTENIMIENTO DE AIRE ACONDICIONADO",
        "tiempo": "5 días restantes",
        "link": "https://prod6.seace.gob.pe/buscador-publico/contrataciones/37498",
        "estado": "Vigente",
        "monto": "S/ 12,500"
    },
    {
        "id": 4,
        "nombre": "CONSULTORÍA PARA LA SUPERVISIÓN DE OBRA VIAL EN CUSCO",
        "tiempo": "Cerrando...",
        "link": "https://prod6.seace.gob.pe/buscador-publico/contrataciones/37485",
        "estado": "Vigente",
        "monto": "S/ 380,000"
    }
]

@app.get("/")
def home():
    return {"status": "ok", "message": "API Licitaciones BDI Activa"}

@app.get("/api/licitaciones")
async def get_licitaciones():
    print("📥 Recibida petición de licitaciones...")
    try:
        # Intentamos hacer el scraping real
        print("🕷️ Intentando scraping...")
        data = await scrape_seace_top_5_paginado()
        
        # Si el scraping devuelve lista vacía (falló silenciosamente), usamos backup
        if not data:
            print("⚠️ Scraping vacío, usando backup.")
            return BACKUP_DATA
            
        print("✅ Scraping exitoso.")
        return data

    except Exception as e:
        # Si el servidor explota (Error 500), capturamos el error y devolvemos el backup
        print(f"❌ ERROR CRÍTICO EN SCRAPER: {e}")
        traceback.print_exc() # Imprime el error real en los logs de Render para que lo leas
        return BACKUP_DATA

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)