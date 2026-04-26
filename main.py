import os
import rioxarray
import xarray as xr
import numpy as np
import pandas as pd
import rasterio

# --- CONFIGURACIÓ DE RUTES ---
# Calcula la ruta on es troba aquest fitxer (main.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Rutes relatives
RAW_BANDS_DIR = os.path.join(BASE_DIR, 'raw_bands_in_Tarragona')
OUTPUT_DIR = os.path.join(BASE_DIR, 'processed_img_Tarragona')
CSV_RESUM_PATH = os.path.join(OUTPUT_DIR, "results_resum.csv")

# Crea la carpeta de sortida si no existeix
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Paràmetre 'a' per a la fórmula de l'EPI (Ajustar segons necessitats)
CONST_A = 1.0

def process_image(band_paths):
    print(f"\n--- Processant imatge Sentinel-2: {band_paths} ---")

    # 1. CARREGAR LES BANDES (Ara afegim la B02 necessària pel SABI)
    try:
        b2 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B02_(Raw).tiff"), masked=True).squeeze()
        b3 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B03_(Raw).tiff"), masked=True).squeeze()
        b4 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B04_(Raw).tiff"), masked=True).squeeze()
        b5 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B05_(Raw).tiff"), masked=True).squeeze()
        b8 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B08_(Raw).tiff"), masked=True).squeeze()
    except rasterio.errors.RasterioIOError as e:
        print(f"Error: No s'han trobat totes les bandes per a: {band_paths}.")
        print(f"RECORDA: Has de descarregar la banda B02 (Blau) de l'EO Browser per calcular el SABI!")
        print(f"Detall de l'error: {e}")
        return

    # 2. CÀLCUL DELS ÍNDEXS
    print("Calculant índexs avançats de qualitat de l'aigua...")
    
    # Assegurem que B05 s'ajusta a la resolució de la resta (per si es descarrega a 20m)
    b5 = b5.rio.reproject_match(b4)

    # Convertim a float32 per evitar errors de divisió per zero
    b2 = b2.astype('float32')
    b3 = b3.astype('float32')
    b4 = b4.astype('float32')
    b5 = b5.astype('float32')
    b8 = b8.astype('float32')

    # Fórmules base corregides
    ndwi = (b3 - b8) / (b3 + b8)
    ndvi = (b8 - b4) / (b8 + b4)
    ndti = (b4 - b3) / (b4 + b3) 
    ndci = (b5 - b4) / (b5 + b4) 

    # Fórmules Avançades de Modelització (Polinòmica i Superficial)
    print("Modelant Clorofil·la-a (CHla) i Potencial d'Eutrofització (EPI)...")
    
    # Concentració de Clorofil·la-a
    chla = 826.57 * (ndci**3) - 176.43 * (ndci**2) + 19 * ndci + 4.071
    
    # Surface Algal Bloom Index (SABI)
    sabi = ((b8 - b4) / (b8 + b4)) - ((b3 - b2) / (b3 + b2))
    
    # SABI Normalitzat
    # Busquem el mínim i màxim real a la imatge per normalitzar entre 0 i 1
    sabi_min = sabi.min()
    sabi_max = sabi.max()
    sabinorm = (sabi - sabi_min) / (sabi_max - sabi_min)
    
    # Eutrophication Potential Index (EPI)
    epi = ((chla / 100) * (1 + CONST_A * sabinorm)) / (1 + ndti)

    # 3. AGRUPAR I FILTRAR DADES
    print("Aplicant màscares i extraient píxels d'alerta...")
    ds = xr.Dataset({
        'ndwi': ndwi,
        'ndvi': ndvi,
        'ndti': ndti,
        'ndci': ndci,
        'chla': chla,
        'sabi': sabi,
        'sabinorm': sabinorm,
        'epi': epi
    })

    # --- UMBRALS DE DETECCIÓ ---
    condicion_agua = ds['ndwi'] > 0.0     
    
    # Com que ara teniu paràmetres més pro, podeu fer saltar l'alerta amb el NDCI o amb el EPI
    # Mantenim l'alerta si hi ha alta clorofil·la base (NDCI > 0.1)
    condicion_alerta = ds['epi'] > 0.4   
    
    mascara_final = condicion_agua & condicion_alerta

    # Aplanem la imatge quedant-nos només amb els píxels en alerta
    df_filtrado = ds.where(mascara_final, drop=True).to_dataframe().dropna().reset_index()

    if df_filtrado.empty:
        print("Cap alerta detectada en aquesta imatge.")
        return

    # 4. PREPARAR EL FORMAT DEL CSV
    # Incorporem TOTES les columnes necessàries usant les coordenades 'x' i 'y' separades per QGIS
    columnes_csv = ['x', 'y', 'ndwi', 'ndvi', 'ndti', 'ndci', 'chla', 'sabi', 'sabinorm', 'epi']
    df_final = df_filtrado[columnes_csv]
    
    # Afegim l'ID de la imatge
    df_final.insert(0, 'imatge_id', band_paths)

    # 5. GUARDAR AL CSV
    df_final.to_csv(CSV_RESUM_PATH, mode='a', header=not os.path.exists(CSV_RESUM_PATH), index=False)
    
    print(f"S'han guardat {len(df_final)} píxels d'alerta al fitxer CSV amb la mètrica EPI.")


if __name__ == "__main__":
    escenes = [
        "2024-11-27-00:00_2024-11-27-23:59_Sentinel-2_L2A"
    ]

    for escena in escenes:
        process_image(escena)
        
    print("Procés acabat!")