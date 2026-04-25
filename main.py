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
        