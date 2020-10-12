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
 - name: Zoran ccccc
   orcid: 0000-0001-7626-4086
   affiliation: UMR 6249 Laboratoire Chrono-environnement, Université Bourgogne Franche-Comté.
date: 12 October 2020
bibliography: paper.bib
---


# Summary

Viewshed analysis is a standard feature of GIS software packages, such as ArcGIS [@ESRI2016], GRASS [@Neteler2012] or @ERDAS2015. However, these implementations vary considerably in terms of their versatility and robustness. Software in the free domain is particularly poor in this respect: visibility analysis is generally implemented as a simple binary query (true/false) for elevation datasets (eg. GRASS or SAGA GIS). In order to meet the demands of a typical analysis concerning visual landscapes we would be interested to find out how deep are certain locations below the visible horizon, what is the overall visual potential of a landscape or which sites are connected in visual networks (cf. @HIGUCHI1983; @Llobera2003; @Cuckovic2015).

Advanced viewshed analysis plug-in for open source Quantum GIS software has been made in order to meet some of these demands: besides standard binary viewshed it provides information on the depth at which objects may be hidden from view, mapping of visual horizon and analysis of intervisibility networks. As of version 0.5.1, the implemented algorithm has been adapted for intensive, repetitive viewshed calculation from multiple observation points.

The plug-in is coded in Python and is dependant of the Quantum GIS framework. More specifically, it makes use of following libraries (bundled with Quantum GIS): numpy, gdal and QGIS core library.   



# References
