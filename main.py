import os
import rioxarray
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓ ---
RAW_BANDS_DIR = os.path.expanduser('~/CassiniHackathon/raw_bands_in/')
OUTPUT_DIR = os.path.expanduser('~/CassiniHackathon/processed_images/')
CSV_RESUM_PATH = os.path.join(OUTPUT_DIR, "results_resum.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

UMBRAL_AGUA = 0.0 # NDWI > 0 es aigua
UMBRAL_EUTROF = 0.15 # NDCI > 0.15 es foco probable de eutrofización

def process_image(band_paths):
    print(f"\n--- Processant imatge Sentinel-2: {band_paths} ---")

    # 1. Carregar les bandes de Sentinel-2
    # Important: Assegureu-vos de descarregar el producte L2A (ja corregit atmosfèricament)
    try:
        b3 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B03.jp2"), masked=True) # Verd
        b4 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B04.jp2"), masked=True) # Vermell
        b5 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B05.jp2"), masked=True) # Red Edge 1
        b8 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B08.jp2"), masked=True) # NIR
    except FileNotFoundError as e:
        print(f"Error: No s'han trobat les bandes per a: {band_paths}. {e}")
        return

    # 2. Alinear resolucions (CRÍTIC per a Sentinel-2)
    # Les bandes 3, 4 i 8 són de 10m/píxel. La banda 5 és de 20m/píxel.
    print("Alineant la resolució de la banda 5 (Red Edge)...")
    b5 = b5.rio.reproject_match(b4)

    # 3. Funció matemàtica segura
    def normalized_diff(banda_a, banda_b):
        num = banda_a - banda_b
        den = banda_a + banda_b
        return num / den.where(den != 0)

    # 4. Calcular índexs natius de Sentinel-2
    print("Calculant índexs de qualitat de l'aigua...")
    ndwi = normalized_diff(b3, b8)  # Màscara d'aigua
    ndvi = normalized_diff(b8, b4)  # Vegetació / Alga superficial
    ndti = normalized_diff(b4, b3)  # Terbolesa
    ndci = normalized_diff(b5, b4)  # Clorofil·la-a (Indicador principal d'eutrofització)

    # 5. Generar Alerta
    alerta_eutroficacion = (ndwi > UMBRAL_AGUA) & (ndci > UMBRAL_EUTROF)

    # 6. Guardar TIFFs (Útils com a fons a QGIS)
    def save_tif(raster, suffix):
        ruta = os.path.join(OUTPUT_DIR, f"{band_paths}_{suffix}.tif")
        raster.rio.to_raster(ruta)

    print("Guardant GeoTIFFs...")
    save_tif(ndwi, "NDWI")
    save_tif(ndci, "NDCI")
    save_tif(ndti, "NDTI")
    save_tif(ndvi, "NDVI")
    save_tif(alerta_eutroficacion.astype(np.uint8), "ALERTA_EUTROFICACIO")

    # =========================================================================
    # 7. EXPORTACIÓ ULTRA-OPTIMITZADA: NOMÉS PÍXELS EN ALERTA PER A QGIS
    # =========================================================================
    print("Generant CSV de punts crítics per a QGIS...")
    
    # Agrupar totes les capes
    ds_pixels = xr.Dataset({
        'NDWI': ndwi,
        'NDCI': ndci,
        'NDTI': ndti,
        'NDVI': ndvi,
        'ALERTA': alerta_eutroficacion
    })

    # Convertir a taula
    df_pixels = ds_pixels.to_dataframe().reset_index()

    # Netejar espais buits (fora de l'òrbita de la imatge)
    df_pixels = df_pixels.dropna(subset=['NDWI'])

    # FILTRE OPTIMITZAT: Quedar-nos exclusivament amb els píxels que són ALERTA
    df_pixels_alerta = df_pixels[df_pixels['ALERTA'] == True]

    # Guardar l'arxiu de punts minúscul i ràpid
    csv_pixel_path = os.path.join(OUTPUT_DIR, f"{band_paths}_pixels_ALERTA_mapa.csv")
    df_pixels_alerta.to_csv(csv_pixel_path, index=False)
    print(f" -> Llest! S'han exportat {len(df_pixels_alerta)} punts d'alerta a {csv_pixel_path}")
    # =========================================================================

    # 8. Registre resum (per al panell de control)
    bounds = b4.rio.bounds() # Utilitzem b4 com a referència espacial
    center_lon = (bounds[0] + bounds[2]) / 2
    center_lat = (bounds[1] + bounds[3]) / 2

    pixels_alerta = int(alerta_eutroficacion.sum().values)

    dades = {
        'id_imatge': band_paths,
        'data_processament': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'latitud_centre': center_lat,
        'longitud_centre': center_lon,
        'pixels_en_alerta': pixels_alerta,
        'risc_global': 'ALT' if pixels_alerta > 1000 else ('MODERAT' if pixels_alerta > 100 else 'BAIX')
    }

    df_resum = pd.DataFrame([dades])
    if not os.path.isfile(CSV_RESUM_PATH):
        df_resum.to_csv(CSV_RESUM_PATH, index=False)
    else:
        df_resum.to_csv(CSV_RESUM_PATH, mode='a', header=False, index=False)

if __name__ == "__main__":
    escenes = ["SENTINEL2_proba"] # Poseu aquí els noms dels vostres arxius sense el _BXX.jp2
    for escena in escenes:
        process_image(escena)