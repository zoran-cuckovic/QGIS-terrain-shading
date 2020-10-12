# Terrain shading: a QGIS plugin for modelling natural illumination over digital terrain models. 


**Repository and download: [github.com/zoran-cuckovic/QGIS-terrain-shading](https://github.com/zoran-cuckovic/QGIS-terrain-shading)**

## Installation

The algorithm for relief shading is available in the official QGIS plugin repository and can be installed as usual (In QGIS go to Plugins -> Manage and install … ). Be sure to enable experimental plugins. 

If the standard installation does not work, the plugin can be downloaded for the repository (above) and installed manually: 
First you need to locate your QGIS plugins folder. On Windows it would be ‘C:\users\username\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins’ (or just do a file search for ‘QGIS3’ …)

Plugin code can then be extracted in a new folder inside the plugins folder (you should name the folder TerrainShading). Take care that the code is not inside a subfolder - the folder structure should be like this:

    QGIS3\profiles\default\python\plugins\
        [some QGIS plugin folders…]
        TerrainShading
            dem_shading.py
            metadata.txt
            [other files and folders…]


Finally, there is a version made as QGIS script, which can be downloaded from the [script branch](https://github.com/zoran-cuckovic/QGIS-terrain-shading/tree/script) and installed as a QGIS script. 

## Manual
See at [zoran-cuckovic.github.io/QGIS-terrain-shading](https://zoran-cuckovic.github.io/QGIS-terrain-shading)

## Tests
To test the algorithm output, you can find a series of models in the Test branch of this repository.



