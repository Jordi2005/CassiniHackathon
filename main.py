import os
import rioxarray
import numpy as np

# Configuration
RAW_BANDS_DIR = '~/CassiniHackathon/raw_bands_in/'
OUTPUT_DIR = '~/CassiniHackathon/processed_images/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Caldra configurar aquests paràmetres segons les necessitats específiques de processament
UMBRAL_AGUA = 0.0; # NDWI > 0 es aigua
UMBRAL_EUTROF = 0.15; # NDCI > 0.15 es foco probable de eutrofización

def process_image(band_paths):
    print(f"Processing image with bands: {band_paths}")

    # Carregar les bandes necessàries
    try:
        b3 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B03.jp2"), masked=True)
        b4 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B04.jp2"), masked=True)
        b5 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B05.jp2"), masked=True)
        b8 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B08.jp2"), masked=True)
    
    except FileNotFoundError as e:
        print(f"Error: No s'han trobat les bandes per a: {band_paths}. {e}")
        return

    # Funcions auxiliars (Gestionar divisions per zero)
    def normalized_diff(banda_a, banda_b):
        denominator = banda_a + banda_b
        # Evitar divisions per zero
        denominator = np.where(denominator != 0, np.nan)
        return (banda_a - banda_b) / denominator
    

    # Calcular indexs
    ndwi = normalized_diff(b3, b8)  # Mascara d'aigua
    ndvi = normalized_diff(b8, b4)   # Vegetació/Algas superficals
    ndti = normalized_diff(b4, b3)  # Turbidez 
    ndci = normalized_diff(b5, b4)  # Cloròfila

    # Generacio del nostre index d'alerta (alerta eutrofització)
    alerta_eutroficacion = (ndwi > UMBRAL_AGUA) & (ndci > UMBRAL_EUTROF)    #calcul que es pot millorar, però és un punt de partida

    # Guardar resultats
    def save_results(raster, suffix):
        raster.rio.to_raster(os.path.join(OUTPUT_DIR, f"{band_paths}_{suffix}.tif"))

        print("Guardando GeoTIFFs...")
        save_results(ndwi, "NDWI")
        save_results(ndvi, "NDVI")
        save_results(ndti, "NDTI")
        save_results(ndci, "NDCI")
        save_results(alerta_eutroficacion.astype(np.uint8), "ALERTA_EUTROFICACIÓ") #uint es fromat boolea (0 o 1)


    print("Iniciando procesamiento de imágenes...")
    #Llista de noms d'escenes
    escenes = ["SENTINEL2_proba"]

    for escena in escenes:
        process_image(escena)
    print("Procesamiento completado.")