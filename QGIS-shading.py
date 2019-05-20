# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterRasterDestination,
                        QgsProcessingParameterBoolean,
                      QgsProcessingParameterNumber
                        )
import processing

import gdal
import numpy as np

class Shading(QgsProcessingAlgorithm):
    """
    Description here
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    DIRECTION= 'DIRECTION'
    ANGLE= 'ANGLE'
    SMOOTH = 'SMOOTH'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return Shading()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'shading'

    def displayName(self): return self.tr('Natural shading ')

    def group(self): return self.tr('Raster terrain analysis')

    def groupId(self): return 'rasterterrainanalysis'

    def shortHelpString(self):
        h = ( """
            <h3>    This algorithm models natural illumination over elevation models, namely shadows.
             
            <b>Input</b> should be an elevation model in raster format. The <b>output</b> will be smoothed where the value of each pixel is averaged with its neighbours whithin the specified radius (smooth radius). Values assigned to the output represent <b>shadow depth</b> below illuminated zones.
    
    <b>    Sun direction</b> and <b>sun angle</b> parmeters define horizontal and vertical position of the sun, where 0° is on the North, 90° on the East and 270° on the West.

            For more information see: <a href="https://landscapearchaeology.org/2019/qgis-shadows/">LandscapeArcaheology.org/2019/qgis-shadows</a>.
            """)
        return self.tr(h)

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT,
                self.tr('Digital elevation model')
            ) )
        
        self.addParameter(QgsProcessingParameterNumber(
            self.DIRECTION,
            self.tr('Sun direction (0 to 360°)'),
            1, 315, False, 0, 360))
            
        self.addParameter(QgsProcessingParameterNumber(
            self.ANGLE,
            self.tr('Sun angle (max = 45°)'),
            1, 10, False, 0, 45))
            
        self.addParameter(QgsProcessingParameterNumber(
            self.SMOOTH,
            self.tr('Smooth radius (pixels)'),
            0, 2, False, 0, 50))  # 0 = QgsProcessingParameterNumber.Integer
        
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
            self.tr("Output file")))

    def processAlgorithm(self, parameters, context, feedback):
        
        
        def view (offset_y, offset_x, shape, step=1):
            """
            Function returning two matching numpy views for moving window routines.
            - offset_y and offset_x refer to the shift in relation to the analysed (central) cell 
            - size_y and size_x refer to the size of the data matrix (not of the window!)
            - view_in is the shifted view and view_out is the position of central cells
            """
            size_y, size_x = shape
             
            x = abs(offset_x)
            y = abs(offset_y)
         
            x_in = slice(x , size_x, step) 
            x_out = slice(0, size_x - x, step)

         
            y_in = slice(y, size_y, step)
            y_out = slice(0, size_y - y, step)
         
            # the swapping trick    
            if offset_x < 0: x_in, x_out = x_out, x_in                                 
            if offset_y < 0: y_in, y_out = y_out, y_in
         
            # return window view (in) and main view (out)
            return np.s_[y_in, x_in], np.s_[y_out, x_out]
      
        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        #if source is None:
         #   raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
                
                # -------------- INPUT -----------------
        elevation_model= self.parameterAsRasterLayer(parameters,self.INPUT, context)
        output_model = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)

        direction = self.parameterAsDouble(parameters,self.DIRECTION, context)
        sun_angle =self.parameterAsDouble(parameters,self.ANGLE, context)
        
        smooth = self.parameterAsBool(parameters,self.SMOOTH, context)
      
        distance_weighting = 0          

        dem = gdal.Open(elevation_model.source())
        mx_z = dem.ReadAsArray().astype(float)

        #should handle better NoData !!
        mx_z[np.isnan(mx_z)]=0

        indices_y, indices_x = np.indices(mx_z.shape)

        if 90 <= direction <= 270: 
            indices_y = indices_y[::-1,:]

        if 180 <= direction <= 360:
            indices_x = indices_x[:, ::-1]
            
        s = direction % 90
        slope = s/45 if s < 45 else (90 - s)/45

        #pixel size : in diagonal
        pixel_size = dem.GetGeoTransform()[1] 
        # adjust for pixel size (in diagonal)
        pixel_size = np.sqrt(pixel_size ** 2 + (pixel_size* slope)**2)

        tilt= np.tan(np.radians(sun_angle)) * pixel_size 

        off_a = indices_x + indices_y * slope 
        off_b = indices_y  + indices_x * slope
        
        steep =  (45 <= direction <= 135 or 225 <= direction <= 315)

        if steep:
            axis = 0  
            off = off_a
              
            src = np.s_[indices_x [:,::-1],
                        off_b.astype(int)]

            mx_temp = np.zeros((np.max(indices_x)+1,
                                np.max(off_b).astype(int)+1))
               
        else :
            axis = 1
            off =  off_b
            src= np.s_[off_a.astype(int), indices_y]


            mx_temp = np.zeros((np.max(off_a).astype(int)+1, 
                                np.max(indices_y)+1))
                                
       
        # distances are x + y , have to divide by two to get pixel distance on x
        off -= off * (slope/2)
        
        mx_z += off[:, ::-1] * tilt
        
        # garbage collection not working (memory leak ???)
        indices_x, indices_y, off_a, off_b = None, None, None, None 
        
        # Update the progress bar
        feedback.setProgress(50)
          
        mx_temp[src] = mx_z; mx_z= None

        mx_temp -=  np.maximum.accumulate(mx_temp, axis=axis)
     
        out = mx_temp[src] ; mx_temp,  src = None, None# memory leaks in QGIS ???
        
        # Update the progress bar
        feedback.setProgress(80)
          
        if smooth:            
            mx_a = np.zeros(out.shape)
            mx_count = np.zeros(out.shape).astype(int)
                      
            for y in range(smooth*2 + 1):
                y_off = y - smooth
                for x in range(smooth* 2 + 1):
                    x_off = x - smooth
                    # if x == r and y==r : continue  #skip center pixel
                    view_in, view_out = view(y_off, x_off, out.shape)

                    mx_a[view_out] += out[view_in]
                    
                    mx_count[view_out] += 1
            
            out = mx_a/mx_count
      
            mx_a, mx_count = None, None# memory leaks in QGIS ???
            
        if distance_weighting:  # not used !!
            iy, ix = np.indices(mx_temp.shape)
            i = ix if not steep else iy #?? swapped  x/y ??
            i2 = np.copy(i); i2[mx_temp < 0] = 0
            mx_temp = (i - np.maximum.accumulate(i2, axis=axis)) * pixel_size
            out2 = mx_temp[src]
       
        # writing output 
        driver = gdal.GetDriverByName('GTiff')
        ds = driver.Create(output_model, out.shape[1], out.shape[0], 1 
        if not distance_weighting else 2, gdal.GDT_Float32)
        ds.SetProjection(dem.GetProjection())
        ds.SetGeoTransform(dem.GetGeoTransform())
        ds.GetRasterBand(1).WriteArray(out)
        if distance_weighting: ds.GetRasterBand(2).WriteArray(out2)
        ds = None
        
        return {self.OUTPUT: output_model}
