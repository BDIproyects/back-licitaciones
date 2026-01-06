import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
from urllib.parse import urljoin

async def scrape_seace_top_5_paginado():
    base_url = "https://prod6.seace.gob.pe/buscador-publico/contrataciones"
    
    # Configurar hora de Perú
    tz_peru = pytz.timezone('America/Lima')
    ahora_peru = datetime.now(tz_peru)
    
    licitaciones_totales = []
    
    print(f"🚀 Iniciando scraping en SEACE...")

    async with async_playwright() as p:
        # Lanzar navegador (headless=True para servidor)
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        try:
            await page.goto(base_url, wait_until="networkidle", timeout=60000)
            
            pagina = 1
            # Buscamos hasta tener 5 o máximo 3 páginas para no saturar
            while len(licitaciones_totales) < 4 and pagina <= 3:
                
                # Esperar selector clave
                try:
                    await page.wait_for_selector("div.bg-fondo-section", timeout=15000)
                except:
                    print("Tiempo de espera agotado esperando selectores.")
                    break

                await page.wait_for_timeout(2000) # Espera extra para Angular
                
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                cards = soup.select("div.bg-fondo-section.rounded-md.p-5")

                for card in cards:
                    if len(licitaciones_totales) >= 4:
                        break

                    # 1. Filtro Vigente
                    if "Vigente" not in card.get_text():
                        continue

                    # 2. Extracción Link
                    link_tag = card.find("a", href=re.compile(r"/buscador-publico/contrataciones/\d+"))
                    enlace = urljoin("https://prod6.seace.gob.pe", link_tag["href"]) if link_tag else "#"

                    # 3. Datos Texto
                    p_tags = card.select("p")
                    # entidad = p_tags[1].get_text(strip=True) if len(p_tags) > 1 else "Entidad desconocida"
                    desc_raw = p_tags[2].get_text(strip=True) if len(p_tags) > 2 else "Sin descripción"
                    desc = re.sub(r"^(Servicio:|Bien:|Obra:|Consultoría:)\s*", "", desc_raw, flags=re.IGNORECASE)

                    # 4. Cálculo Tiempo
                    cotiz_text = ""
                    for p in p_tags:
                        t = p.get_text()
                        if "Cotizaciones:" in t:
                            cotiz_text = t
                    
                    dias_label = "Consultar"
                    fechas = re.findall(r"(\d{2}/\d{2}/\d{4})", cotiz_text)
                    
                    if len(fechas) >= 2:
                        fecha_fin_dt = datetime.strptime(fechas[1], "%d/%m/%Y").date()
                        hoy_peru = ahora_peru.date()
                        diff = (fecha_fin_dt - hoy_peru).days

                        if diff > 0: dias_label = f"{diff} días restantes"
                        elif diff == 0: dias_label = "Vence HOY"
                        else: dias_label = "Cerrado"

                    # AGREGAMOS AL ARRAY CON LAS KEYS CORRECTAS PARA EL FRONTEND
                    licitaciones_totales.append({
                        "id": len(licitaciones_totales),
                        "nombre": desc[:90] + "..." if len(desc) > 90 else desc,
                        "tiempo": dias_label,
                        "link": enlace,
                        "estado": "Vigente",
                        "monto": "Ver detalles" # El scraper original no extraía monto exacto fácil, ponemos placeholder
                    })

                # Paginación
                if len(licitaciones_totales) < 4:
                    btn_next = await page.query_selector("button.mat-mdc-paginator-navigation-next")
                    if btn_next and await btn_next.is_enabled():
                        await btn_next.click()
                        pagina += 1
                        await page.wait_for_timeout(3000)
                    else:
                        break
            
            return licitaciones_totales

        except Exception as e:
            print(f"Error en scraping: {e}")
            return [] # Retornar lista vacía en error para no romper el server
        finally:
            await browser.close()