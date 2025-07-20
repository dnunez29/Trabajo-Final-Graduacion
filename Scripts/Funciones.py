import pandas as pd 
import numpy as np
import re

def normalize_block_name(block_name):
    """
    Función para normalizar nombres de bloques
    """
    if pd.isna(block_name):
        return block_name
    
    # Convertir a mayúsculas y limpiar espacios
    normalized = str(block_name).upper().strip()
    
    # Remover información extra como apartamentos, números adicionales
    normalized = re.sub(r'\s+(APT|UNIT|#|1SRT|2ND)\s*\d*.*$', '', normalized)
    normalized = re.sub(r'\s+\d+$', '', normalized)  # Remover números al final
    
    # Estandarizar abreviaciones comunes
    abbreviation_map = {
        r'\bBLV\b': 'BLVD',
        r'\bAV\b(?!\w)': 'AVE',  # AV pero no AVE
        r'\bSTREET\b': 'ST',
        r'\bAVENUE\b': 'AVE',
        r'\bBOULEVARD\b': 'BLVD',
        r'\bROAD\b': 'RD',
        r'\bDRIVE\b': 'DR',
        r'\bCOURT\b': 'CT',
        r'\bPLACE\b': 'PL',
        r'\bLANE\b': 'LN',
        r'\bLA\b': 'LN',
        r'\bPARKWAY\b': 'PKWY'
    }
    
    for pattern, replacement in abbreviation_map.items():
        normalized = re.sub(pattern, replacement, normalized)
    
    street_suffixes = [' BLVD', ' AVE', ' ST', ' RD', ' DR', ' CT', ' PL', ' LN', ' PKWY']
    for suffix in street_suffixes:
        if suffix in normalized:
            parts = normalized.split(suffix, 1)
            normalized = parts[0] + suffix
            break

    # Limpiar espacios múltiples
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()

