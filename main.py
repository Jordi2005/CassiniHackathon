import os
import rioxarray
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime

# Importar filtre atmosfèric (Assegura't que l'arxiu es diu atmosphere_filter.py)
from atmosphere_filter import aplicar_correccion_6s

# --- CONFIGURACIÓ ---
RAW_BANDS_DIR = os.path.expanduser('~/CassiniHackathon/raw_bands_in/')
OUTPUT_DIR = os.path.expanduser('~/CassiniHackathon/processed_images/')
CSV_RESUM_PATH = os.path.join(OUTPUT_DIR, "results_resum.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

UMBRAL_AGUA = 0.0 # NDWI > 0 es aigua
UMBRAL_EUTROF = 0.15 # NDCI > 0.15 es foco probable de eutrofización

# Metadates simulades
METADATA_DUMMY = {
    'solar_zenith': 35.0, 'solar_azimuth': 160.0, 'sensor_zenith': 0.0, 'sensor_azimuth': 0.0, 'aot': 0.1
}

# Diccionari de bandes d'OpenCosmos 
BANDS_INFO = {
    'B04': {'wl': 499.0, 'fwhm': 19.47},
    'B07': {'wl': 545.0, 'fwhm': 21.08},
    'B08': {'wl': 560.0, 'fwhm': 21.60},
    'B14': {'wl': 649.0, 'fwhm': 24.72},
    'B15': {'wl': 664.0, 'fwhm': 25.24},
    'B18': {'wl': 709.0, 'fwhm': 26.82},
    'B21': {'wl': 755.0, 'fwhm': 28.43},
    'B27': {'wl': 844.0, 'fwhm': 31.54},
    'B28': {'wl': 860.0, 'fwhm': 32.10}
}

def aplicar_correccio_atmosferica(band_xarray, band_id):
    """Extreu la matriu, aplica 6S i la retorna amb coordenades intactes"""
    print(f" -> Corregint {band_id} amb Py6S...")
    wl = BANDS_INFO[band_id]['wl']
    fwhm = BANDS_INFO[band_id]['fwhm']

    # Extraure valors purs, filtrar i reassignar 
    matriu_l1c = band_xarray.values
    matriu_l2a = aplicar_correccion_6s(matriu_l1c, wl, fwhm, METADATA_DUMMY)
    band_xarray.values = matriu_l2a
    return band_xarray

def process_image(band_paths):
    print(f"\nProcessing image with bands: {band_paths}")

    # 1. Carregar les bandes
    try:
        b4 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B04.jp2"), masked=True)
        b7 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B07.jp2"), masked=True)
        b8 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B08.jp2"), masked=True)
        b14 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B14.jp2"), masked=True)
        b15 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B15.jp2"), masked=True)
        b18 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B18.jp2"), masked=True)
        b21 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B21.jp2"), masked=True)
        b27 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B27.jp2"), masked=True)
        b28 = rioxarray.open_rasterio(os.path.join(RAW_BANDS_DIR, f"{band_paths}_B28.jp2"), masked=True)
    except FileNotFoundError as e:
        print(f"Error: No s'han trobat les bandes per a: {band_paths}. {e}")
        return

    # 2. Aplicar correcció atmosfèrica
    b4 = aplicar_correccio_atmosferica(b4, 'B04')
    b7 = aplicar_correccio_atmosferica(b7, 'B07')
    b8 = aplicar_correccio_atmosferica(b8, 'B08')
    b14 = aplicar_correccio_atmosferica(b14, 'B14')
    b15 = aplicar_correccio_atmosferica(b15, 'B15')
    b18 = aplicar_correccio_atmosferica(b18, 'B18')
    b21 = aplicar_correccio_atmosferica(b21, 'B21')
    b27 = aplicar_correccio_atmosferica(b27, 'B27')
    b28 = aplicar_correccio_atmosferica(b28, 'B28')

    # 3. Funcions auxiliars segures
    def normalized_diff(banda_a, banda_b):
        num = banda_a - banda_b
        den = banda_a + banda_b
        return num / den.where(den != 0)

    def three_band_model(b15, b18, b21):
        inv_b15 = 1 / b15.where(b15 != 0)
        inv_b18 = 1 / b18.where(b18 != 0)
        return (inv_b15 - inv_b18) * b21

    # 4. Calcular índexs
    print("Calculant índexs de qualitat de l'aigua...")
    ndwi = normalized_diff(b7, b28)
    ndvi = normalized_diff(b28, b15)
    ndti = normalized_diff(b14, b7)
    ndci = normalized_diff(b18, b15)
    sabi = normalized_diff(b27, b15) - normalized_diff(b8, b4)
    tbm = three_band_model(b15, b18, b21)

    alerta_eutroficacion = (ndwi > UMBRAL_AGUA) & (ndci > UMBRAL_EUTROF)

    # 5. Guardar TIFFs 
    def save_tif(raster, suffix):
        ruta = os.path.join(OUTPUT_DIR, f"{band_paths}_{suffix}.tif")
        raster.rio.to_raster(ruta)

    print("Guardant GeoTIFFs...")
    save_tif(ndwi, "NDWI")
    save_tif(ndci, "NDCI")
    save_tif(tbm, "TBM_CHLA")
    save_tif(alerta_eutroficacion.astype(np.uint8), "ALERTA_EUTROFICACIO")

    # =========================================================================
    # 6. EXPORTACIÓ ULTRA-OPTIMITZADA: NOMÉS PÍXELS EN ALERTA
    # =========================================================================
    print("Generant CSV de punts crítics per a QGIS...")
    
    # Agrupar totes les capes en un únic Dataset
    ds_pixels = xr.Dataset({
        'NDWI': ndwi,
        'NDCI': ndci,
        'SABI': sabi,
        'TBM': tbm,
        'ALERTA': alerta_eutroficacion
    })

    # Convertir a taula 1D amb columnes X, Y, Valors
    df_pixels = ds_pixels.to_dataframe().reset_index()

    # Netejar espais en blanc
    df_pixels = df_pixels.dropna(subset=['NDWI'])

    # FILTRE OPTIMITZAT: Quedar-nos exclusivament amb els píxels que són ALERTA (1 o True)
    df_pixels_alerta = df_pixels[df_pixels['ALERTA'] == True]

    # Guardar l'arxiu de punts (ara serà minúscul i anirà súper ràpid a QGIS)
    csv_pixel_path = os.path.join(OUTPUT_DIR, f"{band_paths}_pixels_ALERTA_mapa.csv")
    df_pixels_alerta.to_csv(csv_pixel_path, index=False)
    print(f" -> Llest! S'han exportat {len(df_pixels_alerta)} punts d'alerta a {csv_pixel_path}")
    # =========================================================================

    # 7. Registre resum (per al panell de control)
    bounds = b15.rio.bounds()
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
    escenes = ["SENTINEL2_proba"]
    for escena in escenes:
        process_image(escena)