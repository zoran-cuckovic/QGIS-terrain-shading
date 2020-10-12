<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis maxScale="0" minScale="1e+08" hasScaleBasedVisibilityFlag="0" styleCategories="AllStyleCategories" version="3.12.0-București">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>0</Searchable>
  </flags>
  <customproperties>
    <property key="WMSBackgroundLayer" value="false"/>
    <property key="WMSPublishDataSourceUrl" value="false"/>
    <property key="embeddedWidgets/count" value="0"/>
    <property key="identify/format" value="Value"/>
  </customproperties>
  <pipe>
    <rasterrenderer classificationMin="-50" alphaBand="-1" opacity="1" classificationMax="0" type="singlebandpseudocolor" nodataColor="" band="1">
      <rasterTransparency>
        <singleValuePixelList>
          <pixelListEntry percentTransparent="100" max="0" min="-2"/>
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
        <colorrampshader classificationMode="2" clip="0" colorRampType="INTERPOLATED">
          <colorramp name="[source]" type="gradient">
            <prop k="color1" v="5,5,5,255"/>
            <prop k="color2" v="64,64,64,255"/>
            <prop k="discrete" v="0"/>
            <prop k="rampType" v="gradient"/>
          </colorramp>
          <item alpha="210" color="#050505" value="-50" label="-50"/>
          <item alpha="185" color="#222222" value="-30" label="-30"/>
          <item alpha="145" color="#313131" value="-10" label="-10"/>
          <item alpha="51" color="#313131" value="-5" label="-5"/>
          <item alpha="26" color="#404040" value="0" label="0"/>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0"/>
    <huesaturation colorizeRed="255" colorizeGreen="128" colorizeOn="0" grayscaleMode="0" colorizeStrength="100" colorizeBlue="128" saturation="0"/>
    <rasterresampler maxOversampling="2"/>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
