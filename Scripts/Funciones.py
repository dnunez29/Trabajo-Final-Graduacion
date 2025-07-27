import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import pandas as pd
import numpy as np
import re
import os
import geopandas as gpd
import contextily as ctx
from shapely.geometry import Point, box
from scipy.stats import gaussian_kde
from scipy.ndimage import gaussian_filter


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

def limpiar_entorno(vars_a_conservar):
    especiales = [k for k in globals().keys() if k.startswith('_') or k in (
        '__builtins__', '__name__', '__doc__', '__package__', '__loader__',
        '__spec__', '__annotations__', '__file__', '__cached__'
    )]
    
    conservar = set(vars_a_conservar) | set(especiales)

    # Creamos un bloque de código que borra las variables que no se van a conservar
    for var in list(globals()):
        if var not in conservar:
            exec(f"del {var}", globals())

def create_grid(bounds, cell_size=500):
    xmin, ymin, xmax, ymax = bounds
    grid_cells = []
    for x0 in range(int(xmin), int(xmax), cell_size):
        for y0 in range(int(ymin), int(ymax), cell_size):
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            grid_cells.append(box(x0, y0, x1, y1))
    return gpd.GeoDataFrame(geometry=grid_cells, crs="EPSG:3857")

def create_heatmap_v1(gdf):

    # Extraer coordenadas para el mapa de calor
    x_coords = gdf.geometry.x
    y_coords = gdf.geometry.y

    # Crear el mapa de calor usando densidad kernel
    fig, ax = plt.subplots(figsize=(12, 10))

    # Crear una grilla para la densidad
    x_min, x_max = x_coords.min(), x_coords.max()
    y_min, y_max = y_coords.min(), y_coords.max()

    # Expandir un poco los límites para mejor visualización
    x_range = x_max - x_min
    y_range = y_max - y_min
    x_min -= x_range * 0.05
    x_max += x_range * 0.05
    y_min -= y_range * 0.05
    y_max += y_range * 0.05

    # Crear grilla para el mapa de calor (ajusta la resolución según necesites)
    xx, yy = np.mgrid[x_min:x_max:100j, y_min:y_max:100j]
    positions = np.vstack([xx.ravel(), yy.ravel()])

    # Crear los datos para el kernel density
    values = np.vstack([x_coords, y_coords])
    kernel = gaussian_kde(values)

    # Calcular la densidad en cada punto de la grilla
    f = kernel(positions)
    f = f.reshape(xx.shape)

    # Crear colormap personalizado (azul -> verde -> amarillo -> rojo)
    colors = ['#000080', '#0066cc', '#00ccff', '#00ff00', '#ffff00', '#ff6600', '#ff0000']
    n_bins = 100
    cmap = LinearSegmentedColormap.from_list('heatmap', colors, N=n_bins)

    # Dibujar el mapa de calor
    im = ax.contourf(xx, yy, f, levels=50, cmap=cmap, alpha=0.7)

    # Alternativamente, puedes usar imshow para un efecto más suave:
    im = ax.imshow(f.T, extent=[x_min, x_max, y_min, y_max], 
               origin='lower', cmap=cmap, alpha=0.7, aspect='auto')

    # Agregar el mapa base
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, alpha=0.6)

    # Configurar el mapa
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    # Agregar barra de colores
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Densidad de Incidentes', rotation=270, labelpad=20, fontsize=12)

    plt.title("Mapa de Calor - Densidad de Incidentes", fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.show()

def create_heatmap(gdf, grid=None, show_grid=True, grid_style='white'):
    # Extraer coordenadas para el mapa de calor
    x_coords = gdf.geometry.x
    y_coords = gdf.geometry.y

    # Crear el mapa de calor usando densidad kernel
    fig, ax = plt.subplots(figsize=(12, 10))

    # Crear una grilla para la densidad con mayor resolución
    x_min, x_max = x_coords.min(), x_coords.max()
    y_min, y_max = y_coords.min(), y_coords.max()

    # Expandir un poco los límites
    x_range = x_max - x_min
    y_range = y_max - y_min
    x_min -= x_range * 0.02
    x_max += x_range * 0.02
    y_min -= y_range * 0.02
    y_max += y_range * 0.02

    # Crear grilla de alta resolución para efectos más suaves
    resolution = 200j
    xx, yy = np.mgrid[x_min:x_max:resolution, y_min:y_max:resolution]
    positions = np.vstack([xx.ravel(), yy.ravel()])

    # Crear kernel density con bandwidth más amplio para efecto blob
    values = np.vstack([x_coords, y_coords])
    kernel = gaussian_kde(values)
    # Ajustar el bandwidth para hacer los blobs más grandes
    kernel.set_bandwidth(kernel.factor * 1.5)

    # Calcular densidad
    f = kernel(positions)
    f = f.reshape(xx.shape)

    # Aplicar filtro gaussiano adicional para mayor suavidad
    f = gaussian_filter(f, sigma=1.5)

    # Crear colormap estilo thermal/heat
    colors = ['#000033', '#000055', '#000077', '#0000BB', '#0022DD', 
            '#0055FF', '#00AAFF', '#00FFAA', '#55FF00', '#AAFF00', 
            '#FFDD00', '#FF8800', '#FF4400', '#FF0000', '#CC0000']
    cmap = LinearSegmentedColormap.from_list('thermal', colors, N=256)

    # Dibujar usando imshow para efecto más suave y blob-like
    im = ax.imshow(f.T, extent=[x_min, x_max, y_min, y_max], 
                origin='lower', cmap=cmap, alpha=0.8, aspect='auto',
                interpolation='gaussian')

    # Agregar el mapa base
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, alpha=0.4)

    # MOSTRAR GRID SI SE PROPORCIONA
    if show_grid and grid is not None:
        # Estilos de grid predefinidos
        grid_styles = {
            'white': {'color': 'white', 'linewidth': 0.5, 'alpha': 0.7},
            'black': {'color': 'black', 'linewidth': 0.4, 'alpha': 0.6},
            'yellow': {'color': 'yellow', 'linewidth': 0.6, 'alpha': 0.8},
            'gray': {'color': 'gray', 'linewidth': 0.4, 'alpha': 0.5},
            'cyan': {'color': 'cyan', 'linewidth': 0.5, 'alpha': 0.7}
        }
        
        # Aplicar estilo del grid
        style = grid_styles.get(grid_style, grid_styles['white'])
        grid.boundary.plot(ax=ax, **style)
        
        print(f"Mostrando grid con {len(grid)} celdas")
    elif show_grid and grid is None:
        print("Advertencia: show_grid=True pero no se proporcionó el grid")

    # Configurar el mapa
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    # Agregar barra de colores
    cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label('Densidad de Incidentes', rotation=270, labelpad=20, fontsize=12)
    cbar.ax.tick_params(labelsize=10)

    # Estilo más limpio
    ax.set_xlabel('Longitud', fontsize=12)
    ax.set_ylabel('Latitud', fontsize=12)
    
    # Título dinámico
    title = "Mapa de Calor - Densidad de Incidentes"
    if show_grid and grid is not None:
        title += " (con Grid)"
    
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.show()