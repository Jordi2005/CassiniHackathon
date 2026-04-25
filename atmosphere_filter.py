import numpy as np
from Py6S import SixS, Geometry, AtmosProfile, AeroProfile, Wavelength

def aplicar_correccion_6s(imagen_l1c, longitud_onda_nm, fwhm_nm, metadatos):
    """
    Filtra (corrige atmosféricamente) una banda satelital L1C a L2A usando Py6S.
    
    Parámetros:
    - imagen_l1c (numpy.ndarray): Matriz 2D con los valores de reflectancia TOA de la banda.
    - longitud_onda_nm (float): Longitud de onda central de la banda en nanómetros (ej. 664.0).
    - fwhm_nm (float): Ancho de banda a media altura en nanómetros (ej. 24.24).
    - metadatos (dict): Diccionario con los ángulos solares y del sensor.
    
    Retorna:
    - imagen_l2a (numpy.ndarray): Matriz 2D corregida (Reflectancia BOA).
    """
    
    # 1. Inicializar el modelo 6S
    s = SixS()
    
    # 2. Configurar Geometría (los ángulos deben venir en los metadatos de Open Cosmos)
    s.geometry = Geometry.User()
    s.geometry.solar_z = metadatos.get('solar_zenith', 30.0)   # Ángulo cenital solar
    s.geometry.solar_a = metadatos.get('solar_azimuth', 180.0) # Azimut solar
    s.geometry.view_z = metadatos.get('sensor_zenith', 0.0)    # Ángulo cenital del sensor (nadir = 0)
    s.geometry.view_a = metadatos.get('sensor_azimuth', 0.0)   # Azimut del sensor
    
    # 3. Configurar Atmósfera y Aerosoles para entorno marino
    s.atmos_profile = AtmosProfile.PredefinedType(AtmosProfile.MidlatitudeSummer)
    s.aero_profile = AeroProfile.PredefinedType(AeroProfile.Maritime)
    s.aot550 = metadatos.get('aot', 0.1)  # Espesor óptico de aerosoles (0.1 es un mar limpio por defecto)
    
    # 4. Configurar la Banda (Py6S requiere micrómetros, así que dividimos nm entre 1000)
    center_um = longitud_onda_nm / 1000.0
    fwhm_um = fwhm_nm / 1000.0
    
    # Calcular el rango de la banda usando el FWHM
    wvl_min = center_um - (fwhm_um / 2.0)
    wvl_max = center_um + (fwhm_um / 2.0)
    
    s.wavelength = Wavelength(wvl_min, wvl_max)
    
    # 5. Ejecutar el modelo de transferencia radiativa
    s.run()
    
    # 6. Extraer los coeficientes de corrección atmosférica
    xa = s.outputs.coef_xa
    xb = s.outputs.coef_xb
    xc = s.outputs.coef_xc
    
    # 7. Aplicar la matemática vectorial a la matriz de la imagen usando numpy
    # Paso A: Calcular la variable intermedia 'y'
    y = (xa * imagen_l1c) - xb
    
    # Paso B: Calcular la reflectancia de superficie (Bottom-of-Atmosphere)
    imagen_l2a = y / (1.0 + (xc * y))
    
    # 8. Limpieza de ruido: Forzar valores negativos a cero (el mar es muy oscuro, a veces el modelo sobrecorrige)
    imagen_l2a = np.where(imagen_l2a < 0, 0, imagen_l2a)
    
    return imagen_l2a
