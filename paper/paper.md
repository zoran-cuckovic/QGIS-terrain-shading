---
title: ‘Terrain Shading: a module for analytical terrain visualisation in QGIS’
tags:
  - GIS
  - lidar
  - elevation model visualisation
  - landscape analysis
  - archaeology 
  - geomorphology
authors:
  - name: Zoran Čučković
    orcid: 0000-0001-7626-4086
    affiliation: Laboratoire Chrono-environnement (UMR 6249), Université de Bourgogne Franche-Comté
date: 13 October 2020
bibliography: references.bib
---
 
![Figure 1. Historic agricultural landscape revealed by analytical shading of Lidar derived terrain model. We can see traces of field boundaries, paths, and some ploughing marks, especially in the upper right corner (Site: environs of Oxford, UK; data: [@Environment_Agency_2020]; methods used: terrain position index (TPI), ambient occlusion and a bit of hillshading.).](fig1.png)


Analytical terrain visualisation is used in various applications, such as cartography, geomorphological analysis or detection of specific surface features. For instance, archaeologists use extensively fine grained terrain models in order to map faint traces of historical activities (Figure 1). Digital terrain models are normally handled and analysed in GIS software (Geographic Information Systems), which is used for the analysis and management of various types of geographic data. QGIS is the most widely used open source GIS software and Terrain Shading module was developed in order to equip the software with several common algorithms for terrain visualisation and feature detection. More specifically, the module features algorithms for hillshade [@Horn_1981], ambient occlusion (also known as sky-view factor: [@Zakšek_&al_2011]), natural shadow, and terrain position index [@Jenness_2006;  @DeReu_&al_2013).  These methods constitute a basic toolbox for analytical terrain visualisation (see esp. [@Kokalj_&_Hesse_2017]). Other algorithms may be included in the future, as well. 

Most of these methods are already available in standard GIS software, but with features and parameters for general use, rather than for analytical terrain visualisation. The algorithms included in the QGIS Terrain Shading module are designed specifically for advanced terrain feature detection and mapping, an approach that is commonly used by archaeologists and geomorphologists, among others [@Kokalj_&_Hesse_2017]. Such methods of surface or terrain analysis often rely on high resolution elevation models, obtained thorough LIDAR scanning or photogrammetry, which entails specific requirements in terms of algorithmic architecture. QGIS terrain shading module aims to provide an integrated toolset for these approaches, as well as for general, wide scale terrain cartography.

## References
