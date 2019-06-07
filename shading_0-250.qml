<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="AllStyleCategories" minScale="1e+08" maxScale="0" version="3.4.0-Madeira" hasScaleBasedVisibilityFlag="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>0</Searchable>
  </flags>
  <customproperties>
    <property value="false" key="WMSBackgroundLayer"/>
    <property value="false" key="WMSPublishDataSourceUrl"/>
    <property value="0" key="embeddedWidgets/count"/>
    <property value="Value" key="identify/format"/>
  </customproperties>
  <pipe>
    <rasterrenderer classificationMax="0" band="1" classificationMin="-250" type="singlebandpseudocolor" opacity="1" alphaBand="-1">
      <rasterTransparency>
        <singleValuePixelList>
          <pixelListEntry min="-2" percentTransparent="100" max="0"/>
        </singleValuePixelList>
      </rasterTransparency>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <rastershader>
        <colorrampshader clip="0" colorRampType="INTERPOLATED" classificationMode="2">
          <colorramp name="[source]" type="gradient">
            <prop k="color1" v="5,5,5,255"/>
            <prop k="color2" v="64,64,64,255"/>
            <prop k="discrete" v="0"/>
            <prop k="rampType" v="gradient"/>
          </colorramp>
          <item color="#050505" value="-250" alpha="210" label="-250"/>
          <item color="#222222" value="-150" alpha="185" label="-150"/>
          <item color="#313131" value="-100" alpha="145" label="-100"/>
          <item color="#313131" value="-20" alpha="51" label="-20"/>
          <item color="#404040" value="0" alpha="26" label="0"/>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast contrast="0" brightness="0"/>
    <huesaturation grayscaleMode="0" colorizeGreen="128" colorizeBlue="128" saturation="0" colorizeRed="255" colorizeOn="0" colorizeStrength="100"/>
    <rasterresampler maxOversampling="2"/>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
