---
title: 'Terrain Shading: a module for analytical terrain visualisation in QGIS'
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
   affiliation: UMR 6249 Laboratoire Chrono-environnement, Université Bourgogne Franche-Comté.
date: 12 October 2020
bibliography: paper.bib
---

![Figure 1. Historic agricultural landscape revealed by analytical shading of Lidar derived terrain model. We can see traces of field boundaries, paths, and some ploughing marks, especially in the upper right corner (Site: environs of Oxford, UK; data: [@EnvironmentAgency]; methods used: terrain position index (TPI), ambient occlusion and a bit of hillshading.).](fig1.png)

## Summary 

Analytical terrain visualisation is used in various applications, such as cartography, geomorphological analysis or detection of specific surface features. For instance, archaeologists use extensively fine grained terrain models in order to map faint traces of historical activities (Figure 1). Digital terrain models are normally handled and analysed in GIS software (Geographic Information Systems), which is used for the analysis and management of various types of geographic data. QGIS is the most widely used open source GIS software and Terrain Shading module was developed in order to equip the software with several common algorithms for terrain visualisation and feature detection. More specifically, the module features algorithms for hillshade [@Horn], ambient occlusion [also known as sky-view factor: @Zaksek], natural shadow, and terrain position index [@Jenness;  @DeReu].  These methods constitute a basic toolbox for analytical terrain visualisation [see esp. @Kokalj&Hesse]. Other algorithms may be included in the future, as well. 

Recent profusion of available elevation data, acquired through Lidar surveys and other remote sensing methods, has stimulated a growing scientific interest in the analysis elevation models. Much of this interest is in the domain of feature detection, as for instance in archaeology, or for terrain cartography and other forms of analytical representation. Such methods of surface or terrain analysis, often relying on high resolution elevation models, require specific algorithmic architecture that meets the demand for speed and versatility. QGIS Terrain Shading module has been designed to meet these needs, as well as to provide a simple, user-friendly, and well documented toolset. Integrated in QGIS, it is easily combined with other GIS algorithms and deployed on an almost endless variety of GIS data formats that the software can read. 

[@rvt]

The algorithms included in QGIS Terrain Shading module can be found in other, already available software, but with features and parameters for general use, rather than for analytical terrain visualisation. Some rather commonplace algorithms have also been refined, for instance hillshade, which can now be adjusted over two axes, parallel and perpendicular to the specified light source. All included algorithms are designed with specific sampling schemes in order to ensure a satisfying execution speed. QGIS Terrain Shading thus builds on existing solutions [e.g. SAGA GIS: @saga or RVT: @rvt], but with adjustments and improvements for advanced terrain feature detection and mapping, an approach that is commonly used by archaeologists and geomorphologists, among others [see esp. @Kokalj&Hesse]. Programmed in Python and integrated in QGIS, this solution can also be considered as "developper friendly", more accessible than software programmed in low level languages and/or distributed in complied version exclusively. Programmed in Python and integrated in QGIS, this solution can also be considered as "developer friendly", more accessible than software programmed in low level languages and/or distributed in complied versions exclusively.     

## References
