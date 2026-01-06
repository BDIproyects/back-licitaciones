import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
from urllib.parse import urljoin
import sys

async def scrape_seace_top_5_paginado():
    base_url = "https://prod6.seace.gob.pe/buscador-publico/contrataciones"
    
    # Configurar hora de Perú
    tz_peru = pytz.timezone('America/Lima')
    ahora_peru = datetime.now(tz_peru)
    
    licitaciones_totales = []
    
    print(f"🚀 Iniciando scraping en SEACE...")

    async with async_playwright() as p:
        # --- CONFIGURACIÓN OPTIMIZADA PARA RENDER (MEMORIA BAJA) ---
        print("Lanzando navegador...")
        browser = await p.chromium.launch(
            headless=True, 
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage', # Clave para Docker/Render
                '--disable-gpu',           # Ahorra memoria
                '--single-process'         # A veces ayuda en entornos limitados
            ]
        )
        
        try:
            # Crear contexto con timeout reducido para no colgar el server
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 720}
            )
            # Timeout por defecto de 30 segundos para todo
            context.set_default_timeout(30000) 
            
            page = await context.new_page()

            print(f"Navegando a {base_url}...")
            # wait_until="domcontentloaded" es más rápido que "networkidle"
            await page.goto(base_url, wait_until="domcontentloaded", timeout=45000)
            
            # Esperar selectores clave
            try:
                print("Esperando selector de tarjetas...")
                await page.wait_for_selector("div.bg-fondo-section", state="attached", timeout=20000)
            except Exception as e:
                print(f"Timeout esperando selector: {e}")
                # Si falla, tomamos captura para debug (opcional) y salimos
                return []

            # Pequeña espera para renderizado dinámico
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            cards = soup.select("div.bg-fondo-section.rounded-md.p-5")
            
            print(f"Tarjetas encontradas: {len(cards)}")

            for index, card in enumerate(cards):
                if len(licitaciones_totales) >= 4:
                    break

                # Filtros y extracción (Código original mantenido)
                if "Vigente" not in card.get_text():
                    continue

                link_tag = card.find("a", href=re.compile(r"/buscador-publico/contrataciones/\d+"))
                enlace = urljoin("https://prod6.seace.gob.pe", link_tag["href"]) if link_tag else "#"

                p_tags = card.select("p")
                desc_raw = p_tags[2].get_text(strip=True) if len(p_tags) > 2 else "Sin descripción"
                desc = re.sub(r"^(Servicio:|Bien:|Obra:|Consultoría:)\s*", "", desc_raw, flags=re.IGNORECASE)

                cotiz_text = ""
                for p in p_tags:
                    t = p.get_text()
                    if "Cotizaciones:" in t:
                        cotiz_text = t
                
                dias_label = "Consultar"
                fechas = re.findall(r"(\d{2}/\d{2}/\d{4})", cotiz_text)
                
                if len(fechas) >= 2:
                    try:
                        fecha_fin_dt = datetime.strptime(fechas[1], "%d/%m/%Y").date()
                        hoy_peru = ahora_peru.date()
                        diff = (fecha_fin_dt - hoy_peru).days
                        if diff > 0: dias_label = f"{diff} días restantes"
                        elif diff == 0: dias_label = "Vence HOY"
                        else: dias_label = "Cerrado"
                    except:
                        pass

                licitaciones_totales.append({
                    "id": index,
                    "nombre": desc[:90] + "..." if len(desc) > 90 else desc,
                    "tiempo": dias_label,
                    "link": enlace,
                    "estado": "Vigente",
                    "monto": "Ver detalles"
                })

            print(f"Retornando {len(licitaciones_totales)} licitaciones.")
            return licitaciones_totales

        except Exception as e:
            print(f"❌ Error CRÍTICO en scraping: {e}")
            # Retornar al menos un dato de error para que el front no muera
            return [{
                "id": 999,
                "nombre": "Error temporal obteniendo datos del SEACE",
                "tiempo": "Reintentando...",
                "link": "#",
                "estado": "Error",
                "monto": "---"
            }]
        finally:
            await browser.close()