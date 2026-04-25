import os
import rioxarray
import numpy as np
import pandas as pd
from datetime import datetime

#Importar filtre atmosfèric 
from atmosphere import atmospheric_correction_6s

# Configuration
RAW_BANDS_DIR = os.path.expanduser('~/CassiniHackathon/raw_bands_in/')
OUTPUT_DIR = os.path.expanduser('~/CassiniHackathon/processed_images/')
CSV_PATH = os.path.join(OUTPUT_DIR, "results.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Caldra configurar aquests paràmetres segons les necessitats específiques de processament
UMBRAL_AGUA = 0.0; # NDWI > 0 es aigua
UMBRAL_EUTROF = 0.15; # NDCI > 0.15 es foco probable de eutrofización

#Metadates simulades (s'haruà de revisar això)
METADATA_DUMMY = {
    'solar_zenith': 35.0, 'solar_azimuth': 160.0, 'sensor_zenith': 0.0, 'sensor_azimuth': 0.0, 'aot': '.1'
}

# Diccionari de caracteristiques de les bandes d'OpenCosmos (nm)
BANDS_INFO = {
    'B07': {'wl': 545.0, 'fwhm': 21.08},
    'B14': {'wl': 649.0, 'fwhm': 24.72},
    'B15': {'wl': 664.0, 'fwhm': 25.24},
    'B18': {'wl': 709.0, 'fwhm': 26.82},
    'B21': {'wl': 755.0, 'fwhm': 28.43},
    'B28': {'wl': 860.0, 'fwhm': 32.10}
}

def aplicar_correccio_atmosferica(band_xarray, band_id):
    """Extreu la matriu, aplica 6S i la retorna amb coordenades intactes"""
    print(f" -> Corregint {banda_id} amb Py6S...")
    wl = BANDS_INFO[banda_id]['wl']
    fwhm = BANDS_INFO[banda_id]['fwhm']


    #Extraure valors purs, filtrar i reassignar
    matriu_l1c = band_xarray.values
    matriu_l2a = aplicar_correccio_atmosferica(matriu_l1c, wl, fwhm, METADATA_DUMMY)
    band_xarray.values = matriu_l2a
    return band_xarray

def process_image(band_paths):
    print(f"Processing image with bands: {band_paths}")

    # Carregar les bandes necessàries
    try:
        b4 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B04.jp2"), masked=True)
        b7 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B07.jp2"), masked=True)
        b8 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B08.jp2"), masked=True)
        b14 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B14.jp2"), masked=True)
        b15 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B15.jp2"), masked=True)
        b18 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B18.jp2"), masked=True)
        b27 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B27.jp2"), masked=True)
        b28 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B28.jp2"), masked=True)
        b21 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B21.jp2"), masked=True)

    
    except FileNotFoundError as e:
        print(f"Error: No s'han trobat les bandes per a: {band_paths}. {e}")
        return

    # Aplicar correcció atmosfèrica a cada banda
    b4 = aplicar_correccio_atmosferica(b4, 'B04')
    b7 = aplicar_correccio_atmosferica(b7, 'B07')
    b8 = aplicar_correccio_atmosferica(b8, 'B08')
    b14 = aplicar_correccio_atmosferica(b14, 'B14')
    b15 = aplicar_correccio_atmosferica(b15, 'B15')
    b18 = aplicar_correccio_atmosferica(b18, 'B18')
    b21 = aplicar_correccio_atmosferica(b21, 'B21')
    b27 = aplicar_correccio_atmosferica(b27, 'B27')
    b28 = aplicar_correccio_atmosferica(b28, 'B28')

    # Funcions auxiliars (Gestionar divisions per zero)
    def normalized_diff(banda_a, banda_b):
        num = band_a - band_b
        den = band_a + band_b
        return num / den.where(den != 0)

    def three_band_model(b15, b18, b21):
        # ((1/B15) - (1/B18)) * B21
        inv_b15 = 1 / b15.where(b15 != 0)
        inv_b18 = 1 / b18.where(b18 != 0)
        return (inv_b15 - inv_b18) * b21
    

    # Calcular indexs
    print("Calculant índexs de qualitat de l'aigua...")
    ndwi = normalized_diff(b7, b28)  # Mascara d'aigua
    ndvi = normalized_diff(b28, b15)   # Vegetació/Algas superficals
    ndti = normalized_diff(b14, b7)  # Turbidez 
    ndci = normalized_diff(b18, b15)  # Cloròfila
    sabi = normalized_diff(b27, b15) - normalized_diff(b8, b4)  # Índice de algas superficiales (SABI)
    tbm = three_band_model(b15, b18, b21)  # Indice de clorofila tocho
    


    # Generacio del nostre index d'alerta (alerta eutrofització)
    alerta_eutroficacion = (ndwi > UMBRAL_AGUA) & (ndci > UMBRAL_EUTROF)    #calcul que es pot millorar, però és un punt de partida

    # Guardar resultats
    def save_tif(raster, suffix):
        ruta = os.path.join(OUTPUT_DIR, f"{band_paths}_{suffix}.tif")
        raster.rio.to_raster(ruta)


        print("Guardando GeoTIFFs...")
        save_tif(ndwi, "NDWI")
        save_tif(ndvi, "NDVI")
        save_tif(ndti, "NDTI")
        save_tif(ndci, "NDCI")
        save_tif(tbm, "TBM_CHLA")
        save_tif(alerta_eutroficacion.astype(np.uint8), "ALERTA_EUTROFICACIÓ") #uint es fromat boolea (0 o 1)

    # Extracció de dades i guardat a csv
    print("Generant registre csv...")
    #Obtenir coordenades del centre de la imatge
    bounds = b15.rio.bounds() # (minx, miny, maxx, maxy)
    center_lon = (bounds[0] + bounds[2]) / 2
    center_lat = (bounds[1] + bounds[3]) / 2

    # Calcular estadistiques de contaminació (només on hi hagi aigua)
    ndci_aigua = ndci.where(ndwi > UMBRAL_AGUA)
    pixels_alerta = int(alerta_eutroficacion.sum().values)

    dades = {
        'id_imatge': band_paths,
        'data_processament': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'latitud_centre': center_lat,
        'longitud_centre': center_lon,
        'ndci_mitja_aigua': float(ndci_aigua.mean().values),
        'pixels_en_alerta': pixels_alerta,
        'risc_global': 'ALT' if pixels_alerta > 1000 else ('MODERAT' if pixels_alerta > 100 else 'BAIX')
    }

   # Afegir al CSV
    df = pd.DataFrame([dades])
    if not os.path.isfile(CSV_PATH):
        df.to_csv(CSV_PATH, index=False)
    else:
        df.to_csv(CSV_PATH, mode='a', header=False, index=False)

    print(f"Procés completat. Risc avaluat: {dades['risc_global']}")

if __name__ == "__main__":
    escenes = ["SENTINEL2_proba"]
    for escena in escenes:
        process_image(escena)