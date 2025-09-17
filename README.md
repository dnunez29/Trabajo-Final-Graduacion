# Análisis Geoespacial de la criminalidad en Filadelfia utilizando los Zip Code Tabulation Areas (Códigos Postales de EE.UU.)

Este repositorio incluye todos los archivos necesarios para trabajar con datos geoespaciales de los ZCTA (ZIP Code Tabulation Areas) de EE. UU., junto con scripts y notebooks en Python para su procesamiento, análisis, visualización y modelado. 
Asimismo, se incluyen un vídeo explicativo del proyecto con el respectivo informe de resultados.

## 📂 Estructura del repositorio

- **Scripts**: en esta carpeta se encuentran los scripts necesarios para la ejecución del trabajo.
    - TFM_DanielNunezVargas_1eraParte: en este primer notebook se detallan los pasos para la construcción de un score de riesgo para la ciudad de Filadelfia
    - TFM_DanielNunezVargas_2daParte: se detallan los hallazgos del análisis geoespacial, así también como los distintos acercamientos con modelos de ML
    - Funciones: un set de funciones personalizadas que se usaron a lo largo del trabajo.
- **Input**: carpeta que identifica los diferentes recursos necesarios para la ejecución del proyecto.
    - Incidents2024: contiene los archivos en formato .shp de los incidentes reportados en Filadelfia de todo el 2024.  
    - Incidents2025: contiene los archivos en formato .shp de los incidentes reportados en Filadelfia desde enero hasta julio de 2025.   
    - ModelingDatasets: contiene dos carpetas más (Train y Test) las cuales identifican los datos utilizados para el entrenamiento y validación del modelo.
    - USACensus: variables socioeconómicas extraidas del Censo Oficial de los EE.UU segregadas por zona postal.  
    - ZIP: contiene los archivos en formato .shp de las geometrías de todas las áreas postales ubicadas en los EE.UU (Es pesado).
- **Video**: Contiene el vídeo exposición, así también como la ppt que fue utilizada y un archivo .txt con el link de vídeo a Youtube, en caso de que se prefiera verlo en línea.
- **Informe**: contiene el informe escrito con los resultados y anexos respectivos.
- **Images**: en esta carpeta se exportaban todas la imágenes y gráficos generados en los notebooks que fueron posteriormente utilizados en el informe.   

## 🛠️ Requerimientos

- El proyecto fue ejectuado utilizando Python 3.12.4 con los siguientes paquetes:

  - pandas 2.3.0
  - numpy 1.26.4
  - matplotlib 3.10.3
  - seaborn 0.13.2
  - scipy 1.16.0
  - geopandas 1.1.1
  - contextily 1.6.2
  - shapely 2.1.1
  - libpysal 4.13.0
  - esda 2.7.1
  - spreg 1.8.3
  - splot 1.1.7
  - optbinning 0.20.1
  - jenkspy 0.4.1
  - scikit-learn 1.4.2
  - imbalanced-learn 0.12.3
  - holidays 0.78
  - tqdm 4.66.4
- Para instalarlos, se incluyó un .txt dentro de la carpeta de Scripts así que basta con abrir la terminal en la carpeta del proyecto y ejecutar: **pip install -r requirements.txt**
  
