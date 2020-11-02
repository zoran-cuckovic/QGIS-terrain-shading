## Test examples for QGIS Terrain Shading module
In this repository you will find test examples for Terrain Shading algorithms. Two elevation models are provided, fine grained, Lidar derived model of Oxfordshire ([LIDAR Composite DTM 2017 - 2m](https://data.gov.uk/dataset/002d24f0-0056-4176-b55e-171ba7f0e0d5/lidar-composite-dtm-2017-2m)), and a coarse DEM for Požega Valley ([SRTM 1 arc second ](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1-arc?qt-science_center_objects=0#qt-science_center_objects)). Elevation models are projected to OSGB 1936 (CRS:27700) and HTRS96 (CRS:3765), respectively. 

## Paramteres for Oxford models

- hillshade_1 : standard parameters (azimuth = 315; sun angle = 45; Longitudinal exaggeration = 1, Lateral exaggeration = 1)
- hillshade_2: same as previous, but with Lateral exaggeration = 10
- TPI_1: standard parameters (method = simple; radius = 5)
- TPI_2: method = height weighted; radius = 5 
- occlusion: standard parameters (radius = 5, denoise = false)

## Paramters for Požega Valley models
- hillshade_1 : standard parameters (azimuth = 315; sun angle = 45; Longitudinal exaggeration = 1, Lateral exaggeration = 1)
- hillshade_2: same as previous, but with Lateral exaggeration = 3
- occlusion: radius = 5; denoise = true
- shadow: standard parameters (azimuth = 315; sun angle = 45; smooth filter = true)
