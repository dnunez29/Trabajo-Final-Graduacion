import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import pandas as pd
import numpy as np
import re
import os
import contextily as ctx
import holidays
import geopandas as gpd
from shapely.geometry import Point, box
from scipy.stats import gaussian_kde
from scipy.ndimage import gaussian_filter
from scipy.stats import chi2_contingency


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

def create_heatmap(gdf, grid=None, show_grid=True, grid_style='white', ax=None):
    # Si no se pasa un ax, crear figura nueva
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 10))

    # Extraer coordenadas
    x_coords = gdf.geometry.x
    y_coords = gdf.geometry.y

    # Límites
    x_min, x_max = x_coords.min(), x_coords.max()
    y_min, y_max = y_coords.min(), y_coords.max()
    x_range = x_max - x_min
    y_range = y_max - y_min
    x_min -= x_range * 0.02
    x_max += x_range * 0.02
    y_min -= y_range * 0.02
    y_max += y_range * 0.02

    # Grilla de alta resolución
    resolution = 200j
    xx, yy = np.mgrid[x_min:x_max:resolution, y_min:y_max:resolution]
    positions = np.vstack([xx.ravel(), yy.ravel()])

    # KDE
    values = np.vstack([x_coords, y_coords])
    kernel = gaussian_kde(values)
    kernel.set_bandwidth(kernel.factor * 1.5)  # suavizado extra
    f = kernel(positions).reshape(xx.shape)
    f = gaussian_filter(f, sigma=1.5)

    # Colormap estilo heat
    colors = ['#000033', '#000055', '#000077', '#0000BB', '#0022DD',
              '#0055FF', '#00AAFF', '#00FFAA', '#55FF00', '#AAFF00',
              '#FFDD00', '#FF8800', '#FF4400', '#FF0000', '#CC0000']
    cmap = LinearSegmentedColormap.from_list('thermal', colors, N=256)

     # Dibujar usando imshow para efecto más suave y blob-like
    im = ax.imshow(f.T, extent=[x_min, x_max, y_min, y_max], 
                origin='lower', cmap=cmap, alpha=0.9, aspect='auto',
                interpolation='gaussian')

    # Agregar el mapa base
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, alpha=0.60)

    # Mostrar grid si corresponde
    if show_grid and grid is not None:
        grid_styles = {
            'white': {'color': 'white', 'linewidth': 0.5, 'alpha': 0.7},
            'black': {'color': 'black', 'linewidth': 0.4, 'alpha': 0.6},
            'yellow': {'color': 'yellow', 'linewidth': 0.6, 'alpha': 0.8},
            'gray': {'color': 'gray', 'linewidth': 0.4, 'alpha': 0.5},
            'cyan': {'color': 'cyan', 'linewidth': 0.5, 'alpha': 0.7}
        }
        style = grid_styles.get(grid_style, grid_styles['white'])
        grid.boundary.plot(ax=ax, **style)
        print(f"Mostrando grid con {len(grid)} celdas")
    elif show_grid and grid is None:
        print("Advertencia: show_grid=True pero no se proporcionó el grid")

    # Configuración final
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.axis("off")  # sin ejes

    plt.tight_layout()

    # Si la función crea la figura, mostrarla
    if ax is None:
        plt.show()
    return ax

def obtener_estacion(fecha):
    mes = fecha.month
    dia = fecha.day

    if (mes == 12 and dia >= 21) or (1 <= mes <= 2) or (mes == 3 and dia < 20):
        return 'winter'
    elif (mes == 3 and dia >= 20) or (4 <= mes <= 5) or (mes == 6 and dia < 21):
        return 'spring'
    elif (mes == 6 and dia >= 21) or (7 <= mes <= 8) or (mes == 9 and dia < 23):
        return 'summer'
    elif (mes == 9 and dia >= 23) or (10 <= mes <= 11) or (mes == 12 and dia < 21):
        return 'autumn'
    
def variablesTemporales(data):
    # Se declaran las condiciones para segregar el dia por periodos
    condiciones = [
    (data['hour'] >= 6 ) & (data['hour'] < 12 ),
    (data['hour'] >= 12 ) & (data['hour'] < 20 ),
    (data['hour'] < 6 ) | (data['hour'] >= 20)
    ]
    # Se definen los periodos posibles
    periodOfTheDay = ['Morning', 'Afternoon', 'Night']
    # Se define el periodo con base en la columna 'hour'
    data["time_of_day"] = np.select(condiciones, periodOfTheDay, default='Unknown') 
    # Convertimos fecha en objeto datetime
    data['date'] = pd.to_datetime(data['date'])
    # Extraemos el día de la semana
    data['day_of_week'] = data['date'].dt.day_name()
    # # Extraemos semana del año
    data['week_of_year'] = data['date'].dt.isocalendar().week
    # # Extraemos mes
    data['month'] = data['date'].dt.month_name()
    # # Extraemos estación del año
    data['season'] = data['date'].apply(obtener_estacion)
    # Se definen los feriados en Filadelfia
    us_holidays = holidays.UnitedStates(years=data['date'].dt.year.unique(),state='PA')
    # Crear la nueva columna que marca si es feriado o no
    data['is_holiday'] = data['date'].dt.date.isin(us_holidays)

    return(data)

def variablesContextuales(data):
    # Diccionario de clasificación
    clasificacion_violencia = {
        'Aggravated Assault No Firearm': 'Violent',
        'Aggravated Assault Firearm': 'Violent',
        'Arson': 'Non-Violent',
        'Robbery Firearm': 'Violent',
        'Robbery No Firearm': 'Violent',
        'Homicide - Criminal': 'Violent',
        'Homicide - Justifiable': 'Violent',
        'Rape': 'Violent',
        'Other Assaults': 'Violent',
        'Offenses Against Family and Children': 'Violent',
        'Other Sex Offenses (Not Commercialized)': 'Violent',
        'Weapon Violations': 'Violent',  # borderline, pero la incluimos como violento

        # Resto son no violentos
        'Thefts': 'Non-Violent',
        'Theft from Vehicle': 'Non-Violent',
        'All Other Offenses': 'Non-Violent',
        'Motor Vehicle Theft': 'Non-Violent',
        'Receiving Stolen Property': 'Non-Violent',
        'Vandalism/Criminal Mischief': 'Non-Violent',
        'Burglary Residential': 'Non-Violent',
        'Burglary Non-Residential': 'Non-Violent',
        'DRIVING UNDER THE INFLUENCE': 'Non-Violent',
        'Fraud': 'Non-Violent',
        'Narcotic / Drug Law Violations': 'Non-Violent',
        'Public Drunkenness': 'Non-Violent',
        'Forgery and Counterfeiting': 'Non-Violent',
        'Disorderly Conduct': 'Non-Violent',
        'Embezzlement': 'Non-Violent',
        'Prostitution and Commercialized Vice': 'Non-Violent',
        'Liquor Law Violations': 'Non-Violent',
        'Vagrancy/Loitering': 'Non-Violent',
        'Gambling Violations': 'Non-Violent'
    }

    data['crimeType'] = data['crime_description'].map(clasificacion_violencia).fillna('Desconocido')
    
    return(data)

def variablesDemograficas(data, zcta_path = "../Input/ZIP/tl_2020_us_zcta520.shp", USACensus_path = "../Input/USACensus/USACensus.csv", USACensus_income_path = "../Input/USACensus/USACensus_IncomeByZCTA.csv", USACensus_Gini_path = "../Input/USACensus/USACensus_GiniIndexByZCTA.csv"):
    gdf = data.to_crs(epsg = 4326)
    zcta = gpd.read_file(zcta_path).to_crs(epsg=5070) # https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2024&layergroup=ZIP+Code+Tabulation+Areas
    # Se renombra para evitar conflicto
    zcta = zcta[['ZCTA5CE20', 'geometry']]
    # Ahora se calcula el área para cada polígono
    zcta['area_mile2'] = zcta.geometry.area/ 2_589_988.110336
    # Se convierte la pasada geometria a coordinadas lat/lon
    zcta_lat_lon = zcta.to_crs(epsg=4326)
     # Se procede con un JOIN espacial
    gdf_joined = gpd.sjoin(gdf, zcta_lat_lon, how="left", predicate='within')
    # Se extraen coordenadas por aparte
    gdf_joined['lon'] = gdf_joined.geometry.x
    gdf_joined['lat'] = gdf_joined.geometry.y
    
    # KEY CHANGE: Replace point geometry with ZCTA polygon geometry
    # First, merge with zcta_lat_lon to get the ZCTA geometries
    gdf_with_zcta_geom = gdf_joined.merge(
        zcta_lat_lon[['ZCTA5CE20', 'geometry']], 
        on='ZCTA5CE20', 
        how='left',
        suffixes=('_point', '_zcta')
    )
    
    # Drop the original point geometry and rename ZCTA geometry
    gdf_with_zcta_geom = gdf_with_zcta_geom.drop('geometry_point', axis=1)
    gdf_with_zcta_geom = gdf_with_zcta_geom.rename(columns={'geometry_zcta': 'geometry'})
    
    # Ensure it's still a GeoDataFrame with the correct geometry column
    gdf = gpd.GeoDataFrame(gdf_with_zcta_geom, geometry='geometry')
    # Se renombra por simplicidad
    gdf = gdf.rename(columns={'ZCTA5CE20': 'ZCTA'})
    # Se eliminan las columnas que no serán de utilidad
    gdf = gdf.drop(['index_right', 'crime_code', 'location_b'], axis=1)
    # Se importa la información del Censo Oficial de USA
    USACensus = pd.read_csv(USACensus_path, skiprows=1, header=0)
    # Cambiar nombre de columna
    USACensus = USACensus.rename(columns={
    'Geographic Area Name': 'ZCTA',
    'Count!!SEX AND AGE!!Total population' : 'population',
    'Count!!MEDIAN AGE BY SEX!!Both sexes' : 'median_age',
    'Count!!RACE!!Total population!!One Race!!White' : 'white_race_population',
    'Count!!RACE!!Total population!!One Race!!Black or African American' : 'black_race_population',
    'Count!!RACE!!Total population!!One Race!!Asian' : 'asian_race_population',
    'Count!!HISPANIC OR LATINO!!Total population!!Hispanic or Latino (of any race)': 'latino_race_population'})
    # Eliminar el patrón "ZCTA5 " de todos los valores de esa columna
    USACensus['ZCTA'] = USACensus['ZCTA'].str.replace('ZCTA5 ', '', regex=False)
    # Se toma el ZIP Code y la poblacion total para dicha area
    USACensus_Total_Population = USACensus[['ZCTA', 'population', 'white_race_population','black_race_population', 'asian_race_population','latino_race_population']]
    # Se hace el JOIN con el ZCTA como llave
    gdf_with_population = gdf.merge(USACensus_Total_Population, on='ZCTA', how='left')
    # Se calcula la densidad poblacional por area de ZIP Code
    gdf_with_population['density_mile2'] = gdf_with_population['population'] / gdf_with_population['area_mile2'] 

    # Se importa la información oficial del ingreso por ZCTA de USA https://data.census.gov/table/ACSDT5Y2023.B19083?q=median+income&g=040XX00US42$8600000&tp=true
    USACensus_IncomeByZCTA = pd.read_csv(USACensus_income_path, skiprows=1, header=0)
    # Cambiar nombre de columna
    USACensus_IncomeByZCTA = USACensus_IncomeByZCTA.rename(columns={
        'Geographic Area Name': 'ZCTA',
        'Estimate!!Households!!Total' : 'households',
        'Estimate!!Households!!Total!!Less than $10,000' : 'household_10k_or_less',
        'Estimate!!Households!!Total!!$10,000 to $14,999' : 'household_10k_to_15k',
        'Estimate!!Households!!Total!!$15,000 to $24,999' : 'household_15k_to_25k',
        'Estimate!!Households!!Total!!$25,000 to $34,999' : 'household_25k_to_35k',
        'Estimate!!Households!!Total!!$35,000 to $49,999': 'household_35k_to_50k',
        'Estimate!!Households!!Total!!$50,000 to $74,999': 'household_50k_to_75k',
        'Estimate!!Households!!Total!!$75,000 to $99,999': 'household_75k_to_100k', 
        'Estimate!!Households!!Total!!$100,000 to $149,999': 'household_100k_to_150k',
        'Estimate!!Households!!Total!!$150,000 to $199,999': 'household_150k_to_200k', 
        'Estimate!!Households!!Total!!$200,000 or more': 'household_200k_or_more',
        'Estimate!!Households!!Median income (dollars)': 'median_income',
        'Estimate!!Households!!Mean income (dollars)': 'mean_income'})
    # Eliminar el patrón "ZCTA5 " de todos los valores de esa columna
    USACensus_IncomeByZCTA['ZCTA'] = USACensus_IncomeByZCTA['ZCTA'].str.replace('ZCTA5 ', '', regex=False)
    # Agrupamos la informacion de ingreso en grupos más grandes para redecir cardinaldidad de la base final
    USACensus_IncomeByZCTA['household_25k_or_less'] = pd.to_numeric(USACensus_IncomeByZCTA['household_10k_or_less'], errors="coerce") +  pd.to_numeric(USACensus_IncomeByZCTA['household_10k_to_15k'], errors='coerce') + pd.to_numeric(USACensus_IncomeByZCTA['household_15k_to_25k'] , errors='coerce')
    USACensus_IncomeByZCTA['household_25k_to_50k'] = pd.to_numeric(USACensus_IncomeByZCTA['household_25k_to_35k'], errors='coerce') + pd.to_numeric(USACensus_IncomeByZCTA['household_35k_to_50k'], errors='coerce') 
    USACensus_IncomeByZCTA['household_50k_to_150k'] = pd.to_numeric(USACensus_IncomeByZCTA['household_50k_to_75k'], errors='coerce') + pd.to_numeric(USACensus_IncomeByZCTA['household_75k_to_100k'], errors='coerce') + pd.to_numeric(USACensus_IncomeByZCTA['household_100k_to_150k'], errors='coerce')
    USACensus_IncomeByZCTA['household_150k_or_more'] = pd.to_numeric(USACensus_IncomeByZCTA['household_150k_to_200k'], errors='coerce') + pd.to_numeric(USACensus_IncomeByZCTA['household_200k_or_more'], errors='coerce') 
    # Se toma el ZCTA Code y la poblacion total para dicha area
    USACensus_IncomeByZCTA = USACensus_IncomeByZCTA[['ZCTA', 'median_income', 'mean_income', 'households', 'household_25k_or_less', 'household_25k_to_50k', 'household_50k_to_150k', 'household_150k_or_more' ]]
    # Se hace el join con la base de poblacion
    gdf_with_population_and_income = gdf_with_population.merge(USACensus_IncomeByZCTA, on="ZCTA", how='left')

    # Se importa la información de Índice de Gini de USA por ZCTA https://data.census.gov/table/ACSDT5Y2023.B19083?q=median+income&g=040XX00US42$8600000&moe=false
    USACensus_GiniIndex_wide_format = pd.read_csv(USACensus_Gini_path, header=0)
    # Se transpone la base de datos para tener el ZCTA en las filas y el Indice Gini en las columnas
    USACensus_GiniIndex = USACensus_GiniIndex_wide_format.melt(
        id_vars="Label (Grouping)", 
        var_name="ZCTA", 
        value_name="Gini Index")
    # Se remueve la columna repetida
    USACensus_GiniIndex = USACensus_GiniIndex.drop(columns=["Label (Grouping)"])
    # Se renombran los campos
    USACensus_GiniIndex = USACensus_GiniIndex.rename(columns={
        'Label (Grouping)' : 'ZCTA',
        'Gini Index': 'GiniIndex'
    })
    # Se extrae el ZCTA code de la columna ZCTA
    USACensus_GiniIndex["ZCTA"] = USACensus_GiniIndex["ZCTA"].str.extract(r"(\d{5})")
    # Se hace el join con la base de poblacion e income
    gdf_with_all_features = gdf_with_population_and_income.merge(USACensus_GiniIndex, on="ZCTA", how='left')

    return(gdf_with_all_features)

def robust_minmax_with_params(s, q1, q99):
    s_clipped = s.clip(lower=q1, upper=q99)
    denom = (q99 - q1) if (q99 - q1) != 0 else 1.0
    return (s_clipped - q1) / denom

def categorize(p, thresholds):
    if p <= thresholds['low_threshold']:
        return 'Low'
    elif p <= thresholds['high_threshold']:
        return 'Moderate'
    else:
        return 'High'
    
def cleanDataframe(data):

    data = gpd.GeoDataFrame(data, crs='EPSG:4326')

    # Parse dates and ensure correct types
    data['date'] = pd.to_datetime(data['date'], errors='coerce')

    # Sanity checks and minimal cleaning
    num_cols = ['dc_dist', 'hour', 'ZCTA', 'area_mile2', 'population', 'density_mile2']
    for c in num_cols:
        if c in data.columns:
            data[c] = pd.to_numeric(data[c], errors='coerce')

    # Ensure categorical harmonization
    data['crimeType'] = data['crimeType'].str.title()

    # Keep only rows with non-null population and area to avoid divide-by-zero later
    data = data[(data['population'].notna()) & (data['population'] > 0) & (data['area_mile2'].notna()) & (data['area_mile2'] > 0)]
    print('Filtered to rows with positive population and area. Shape:', data.shape)

    return(data)

def apply_risk_indicator(df_new, fitted_params):
    df_new['date'] = pd.to_datetime(df_new['date'], errors='coerce')
    num_cols = ['dc_dist', 'hour', 'ZCTA', 'area_mile2', 'population', 'density_mile2']
    for c in num_cols:
        if c in df_new.columns:
            df_new[c] = pd.to_numeric(df_new[c], errors='coerce')
    df_new['crimeType'] = df_new['crimeType'].str.title()
    df_new = df_new[(df_new['population'] > 0) & (df_new['area_mile2'] > 0)]

    grp_keys = ['ZCTA', 'time_of_day']
    agg = df_new.groupby(grp_keys).size().reset_index(name='crime_count')

    zcta_denom = df_new.groupby('ZCTA').agg(
        population=('population','median'),
        area_mile2=('area_mile2','median'),
        density_mile2=('density_mile2','median')
    ).reset_index()
    agg = agg.merge(zcta_denom, on='ZCTA', how='left')

    agg['exposure_capita'] = agg['population']
    agg['exposure_area'] = agg['area_mile2']

    # Use stored priors
    alpha_capita, beta_capita = fitted_params['alpha_capita'], fitted_params['beta_capita']
    alpha_area, beta_area = fitted_params['alpha_area'], fitted_params['beta_area']

    agg['rate_capita_post'] = (alpha_capita + agg['crime_count']) / (beta_capita + agg['exposure_capita'])
    agg['rate_area_post'] = (alpha_area + agg['crime_count']) / (beta_area + agg['exposure_area'])

    violence_grp = df_new.groupby(['ZCTA','time_of_day']).apply(
        lambda g: np.mean(g['crimeType'].eq('Violent'))
    ).reset_index(name='violent_share')
    agg = agg.merge(violence_grp, on=['ZCTA','time_of_day'], how='left')
    agg['violent_share'] = agg['violent_share'].fillna(0.0)

    # Normalize with train quantiles
    q_params = fitted_params['q_params']
    agg['capita_norm'] = robust_minmax_with_params(agg['rate_capita_post'], *q_params['rate_capita_post'])
    agg['area_norm'] = robust_minmax_with_params(agg['rate_area_post'], *q_params['rate_area_post'])
    agg['density_norm'] = robust_minmax_with_params(agg['density_mile2'], *q_params['density_mile2'])
    agg['violent_norm'] = robust_minmax_with_params(agg['violent_share'], *q_params['violent_share'])

    agg['risk_score'] = (
        0.35 * agg['capita_norm'] +
        0.35 * agg['area_norm'] +
        0.15 * agg['density_norm'] +
        0.15 * agg['violent_norm']
    )

    aggregate_grouped = agg.groupby(['ZCTA']).agg({
    'risk_score':'mean'
    }).reset_index()

    Q1 = agg['risk_score'].quantile(0.25)
    Q3 = agg['risk_score'].quantile(0.75)
    IQR = Q3 - Q1

    # Definir límites
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    # Reemplazar outliers por NaN
    agg['risk_score'] = agg['risk_score'].mask(
        (agg['risk_score'] < lower_bound) | (agg['risk_score'] > upper_bound),
        np.nan
    )

    # Unir agg con aggregate_grouped para tener el promedio de cada ZCTA
    agg = agg.merge(
        aggregate_grouped,
        on='ZCTA',
        how='left',
        suffixes=('', '_mean')
    )

    # Reemplazar NaN en risk_score con el promedio de su ZCTA
    agg['risk_score'] = agg['risk_score'].fillna(agg['risk_score_mean'])

    # Opcional: eliminar columna auxiliar si ya no la necesitas
    agg = agg.drop(columns=['risk_score_mean'])

    # Apply stored thresholds
    thresholds = fitted_params['thresholds']
    def categorize(p):
        if p <= 0.5: # thresholds['low_threshold']:
            return 'Low'
        # elif p <= thresholds['high_threshold']:
        #     return 'Moderate'
        else:
            return 'High'
    agg['risk_level'] = agg['risk_score'].apply(categorize)

    return agg

def cleanDataframe2(df: pd.DataFrame):
    # Renombrar columnas
    rename_map = {
        'dispatch_d' : 'date',
        'crime_desc' : 'crime_description',
        'time_of_da' : 'time_of_day',
        'day_of_wee' : 'day_of_week',
        'week_of_ye': 'week_of_year',
        'latino_rac' : 'latino_race',
        'density_mi' : 'density_mile2',
        'median_inc' : 'median_income',
        'mean_incom': 'mean_income',
        'households' : 'total_households',
        'household_' : 'household_25k_or_less',
        'househol_1' : 'household_25k_to_50k',
        'househol_2' : 'household_50k_to_150k',
        'househol_3' : 'household_150k_or_more',  
    }
    df = df.rename(columns=rename_map)
    
    # Convertir a numérico
    numeric_cols = ['GiniIndex', 'median_income', 'mean_income']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

def chi2_cramersv(df, target, cat_vars):
    results = []
    
    for var in cat_vars:
        # Contingency table (without margins)
        ctabla = pd.crosstab(df[var], df[target])
        
        # Chi² test
        chi2, p, dof, expected = chi2_contingency(ctabla)
        
        # Cramér’s V
        n = ctabla.to_numpy().sum()
        phi2 = chi2 / n
        r, k = ctabla.shape
        cramers_v = np.sqrt(phi2 / min(k - 1, r - 1))
        
        results.append((var, p, cramers_v))
    
    return pd.DataFrame(results, columns=["variable", "p_value", "cramers_v"])

def optimal_binning(X_train, y_train, variable):
    """Crear optimal binning para una variable"""
    optb = OptimalBinning(name=variable, dtype="numerical", solver="cp")
    optb.fit(X_train[variable], y_train)
    
    binning_table = optb.binning_table
    binning_table.build()
    
    return optb, binning_table