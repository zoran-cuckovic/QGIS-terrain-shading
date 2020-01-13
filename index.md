# Terrain shading: a QGIS plugin for modelling natural illumination over digital terrain models.

**Current version: 0.1**

**Supported QGIS version: 3.x**

**Repository and download: [github.com/zoran-cuckovic/QGIS-terrain-shading](https://github.com/zoran-cuckovic/QGIS-terrain-shading)**

![FIGURE SHADOWS](/Dalmacija.jpg)

## Installation

The algorithm is available in the official QGIS plugin repository and can be installed as usual (In QGIS go to Plugins -> Manage and install … ). Be sure to enable experimental plugins. 

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

*Data input* for the plugin should be a digital elevation model (DEM) in raster format. Note that it has to be **projected in a metric coordinate system**. 

*Sun direction* marks the horizontal position of the Sun where 0° is on the North, 90° on the East and 270° on the West.

*Sun angle* marks the vertical position of the Sun. 

*Smooth filter* is a simple 3x3 average filter which eliminates noise and sharp transitions in the output. 

<!-- Two *analysis types* are available. The *shadow depth* will calculate the vertical difference between shadow surface and underlying terrain, while the *shadow length* will calculate the horizontal reach of the shadow. The reach is expressed as horizontal distance and not as slope length from the occlusion point to shadow tip.    -->

*Data output* is in the same raster format as the input dataset.


## Remarks 

For cartographic uses, the best result is achieved when varying levels of transparency according to shadow depth or length. You can download and apply **QGIS style definition** files from the [style library in this repository](https://github.com/zoran-cuckovic/QGIS-terrain-shading/tree/styles).

<!--
The algorithm output may contain some sharp transitions or visible artefacts, especially when made for rugged terrain, over noisy elevation models, such as Lidar data, or over small scale models of urban architecture. A simple 3x3 average (smoothing) filter should be applied in these cases.   
-->

## More information

For tutorials and in-depth discussion see [LandscapeArchaeology.org/2019/qgis-shadows](https://LandscapeArchaeology.org/2019/qgis-shadows/).

Style library can be found in the [GitHub repo](https://github.com/zoran-cuckovic/QGIS-terrain-shading/tree/styles).

You can signal an issue in [GitHub repository](https://github.com/zoran-cuckovic/QGIS-raster-shading/issues).

## Support & donations

If this piece of software makes you a happier cartographer, please consider supporting its developpement by making a small contribution.

<form action="https://www.paypal.com/cgi-bin/webscr" method="post" target="_top">
<input type="hidden" name="cmd" value="_s-xclick" />
<input type="hidden" name="hosted_button_id" value="PM4YE7ZTPGLAU" />
<input type="image" src="https://www.paypalobjects.com/en_US/FR/i/btn/btn_donateCC_LG.gif" border="0" name="submit" title="PayPal - The safer, easier way to pay online!" alt="Donate with PayPal button" />
<img alt="" border="0" src="https://www.paypal.com/en_FR/i/scr/pixel.gif" width="1" height="1" />
</form>
