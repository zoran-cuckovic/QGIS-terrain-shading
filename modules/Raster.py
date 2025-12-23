# -*- coding: utf-8 -*-

"""
/***************************************************************************
TerrainShading
A QGIS plugin
begin : 2021-02-01
copyright : (C) 2021 by Zoran Čučković
email : /
***************************************************************************/

/***************************************************************************
* *
* This program is free software; you can redistribute it and/or modify *
* it under the terms of the GNU General Public License as published by *
* the Free Software Foundation version 2 of the License, or *
* any later version. *
* *
***************************************************************************/
"""

from processing.core.ProcessingConfig import ProcessingConfig
try:
    from osgeo import gdal
except ImportError:
    import gdal
import numpy as np

# buffer modes
DUMP = 0
ADD = 1
MIN = 2 # not used
MAX = 3 # not used

# number formats
FLOAT = gdal.GDT_Float32
BYTE = gdal.GDT_Byte
INT = gdal.GDT_Int16

"""
Memento : 
        NP2GDAL_CONVERSION = {
          "uint8": 1,
          "int8": 1,
          "uint16": 2,
          "int16": 3,
          "uint32": 4,
          "int32": 5,
          "float32": 6,
          "float64": 7,
          "complex64": 10,
          "complex128": 11,
        }

"""

class Raster:    
    def __init__(self, qgis_raster_object,
                 crs=None):

        self.qrst = qgis_raster_object
        
        gdal_raster=gdal.Open(qgis_raster_object.source())
        
        if gdal_raster == None:
            raise Exception("*** Elevation model cannot be opened ! ***")
        
        self.rst = gdal_raster #for speed, keep open raster ?
                        
        # ! attention: x in gdal is y dimension un numpy (the first dimension)
        xs , ys = gdal_raster.RasterXSize , gdal_raster.RasterYSize
        self.xsize, self.ysize = xs, ys
        
        gt=gdal_raster.GetGeoTransform()
            
        #adfGeoTransform[0] /* top left x */
        #adfGeoTransform[1] /* w-e pixel resolution */
        #adfGeoTransform[2] /* rotation, 0 if image is "north up" */
        #adfGeoTransform[3] /* top left y */
        #adfGeoTransform[4] /* rotation, 0 if image is "north up" */
        #adfGeoTransform[5] /* n-s pixel resolution */

        self.pix_x, self.pix_y = abs(gt[1]), abs(gt[5]) 
        # this is meaningless for WGS 84 !
        # self.pix_diag = np.sqrt( self.pix_x**2 + self.pix_y**2)
                
        raster_x_min = gt[0]
        raster_y_max = gt[3] # it's top left y, so maximum!

        raster_y_min = raster_y_max - ys * self.pix_y
        raster_x_max = raster_x_min + xs * self.pix_x

                
        self.extent = [raster_x_min, raster_y_min, 
                       raster_x_max, raster_y_max]

        self.min, self.max = gdal_raster.GetRasterBand(1
                            ).GetStatistics(True, True)[:2]

         # Could also : 
##        raster_max= ..GetRasterBand(1).GetMaximum()
##        raster_min = ..GetRasterBand(1).GetMinimum()
##
        self.nodata = gdal_raster.GetRasterBand(1).GetNoDataValue()
##
##        data_type =  ..GetRasterBand(1).DataType
        
   
        # set processing chunks and the buffer
        chunk = int(ProcessingConfig.getSetting('DATA_CHUNK')) * 1000000
        buffer =  int(ProcessingConfig.getSetting('BUFFER_SIZE')) * 1000000
        self.chunk_x = min(chunk // xs, xs)
        self.chunk_y = min( chunk // ys, ys) 
        if xs * ys <= buffer:
            self.buffer = np.zeros((ys, xs))
        else: 
            self.buffer = None
        

     
    def verify_raster (self):
               
        err, fatal = '', False
   
        units = self.qrst.crs().mapUnits() 
             
        if units != 0 :
            err = " \n ****** \n ERROR! \n Raster data should be projected in a metric system!"
            
            # try a fix for WGS : calculate pixel size in meters 
            # ( which is not the ideal solution ! )
            if units == 6:
                self.pix_x, self.pix_y = self.deg_to_m(self.pix_x, self.pix_y, 
                                    (self.extent[3] + self.extent[1]) /2)
            
        if  round(abs(self.pix_x), 2) !=  round(abs(self.pix_y), 2):
            
            err += (" \n ****** \n ERROR! \n Raster pixels are irregular in shape " +
                  "(probably due to incorrect projection)!")
            
        return err, fatal
    
    """
    Load a chunk 
    """         
    def take (self, gdal_take, matrix_in, fill_nodata=None, data_type = float):
        
        bd = self.rst.GetRasterBand(1)
        bd.ReadAsArray(*gdal_take, matrix_in).astype(data_type)
        
        if not fill_nodata is None: 
            
            matrix_in[matrix_in == self.nodata] = fill_nodata 
            
            # DANGER : handling the common problem of implicit nodata (not registered) 
            matrix_in[matrix_in < -9990] = fill_nodata
         
        return matrix_in
        
    def add_to_buffer(self, matrix, gdal_put, 
                      mode = DUMP, 
                      automatic_save = True):
        """
        Save to buffered numpy array (or directly to disk if the array is too large)
        Attention : automatic save is executed when the end of raster is reached,
        which does not work with reverse reading (back to front). Use write_output() to force saving.
        """
        
        x, y, x_off, y_off = gdal_put 
        try:
                      
            view =  self.buffer [y : y + y_off , x : x + x_off] 
            
            if mode == DUMP: view[:] = matrix
            elif mode == ADD : view += matrix
      
        except: 
           
            bd = self.gdal_output.GetRasterBand(1)
            if mode == ADD: 
                matrix += bd.ReadAsArray(*gdal_put)
                
            bd.WriteArray(matrix, *gdal_put[:2])
            bd.FlushCache() # Important, otherwise it's not saving
            
        
        
        if automatic_save and x + x_off == self.xsize and y + y_off == self.ysize :
            self.write_output()   

    
    def set_output (self, file_name,
                     no_data = np.nan,
                     data_format_override = None,
                     compression = True):
        """
         Prepare output file and set number format. No saving is made at this stage.
         It vill provide a handle (self.gdal_output) which can be used to control writing to disk.
       
        """
        
        if data_format_override:
            self.data_format = data_format_override
        else : 
            self.data_format = INT if ProcessingConfig.getSetting('CONVERT_INT') else FLOAT
        
         # Create immediately the output. 
        driver = gdal.GetDriverByName('GTiff')

        options = ['COMPRESS=LZW' if compression else '']

        if self.xsize * self.ysize > 5e8 : 
        
            options += [
                    'BIGTIFF=YES',          # <-- this is the key!
                    'TILED=YES',            # recommended for large rasters
                    'BLOCKXSIZE=256',       # optional, for better I/O
                    'BLOCKYSIZE=256'
                ]
      
        ds = driver.Create(file_name, self.xsize, self.ysize, 
                           1, self.data_format, options)

        ds.SetProjection(self.rst.GetProjection())
        ds.SetGeoTransform(self.rst.GetGeoTransform())

        ds.GetRasterBand(1).SetNoDataValue(no_data)           
        #ds.GetRasterBand(1).Fill(self.fill)
        
        self.gdal_output = ds    # a handle for adding data 
        
        
    
    def write_output(self):

        if isinstance(self.buffer, np.ndarray): # buffered mode

            # convert formats (normalise first)
            # conversion when working outside the buffer is NOT implemented yet. 
            if self.data_format != FLOAT : 
                sd, max_val, median = np.std(self.buffer), np.max(abs(self.buffer)), np.median(self.buffer)
                if max_val > median  +  5 * sd : max_val = median  +  5 * sd 
                self.buffer /= max_val
                if self.data_format == INT:  self.buffer *= 32767 
                elif self.data_format == BYTE: self.buffer *= 255 

            self.gdal_output.GetRasterBand(1).WriteArray(self.buffer)
            
        self.gdal_output = None # to save the raster (buffered or non-buffered)
            
            

    def deg_to_m(self, diff_x, diff_y, latitude):
        """
        Converts length and width from Lat/Lon to meters (e.g. pixel size)
        """
        # https://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters/2964#2964
        # 1 deg = 111,111 km
      
        return (diff_x * 111111 * np.cos(np.radians(latitude)) , 
                diff_y * 111111 )
        
    def angle_adjustment(self, angle):
        """
        Adjust angular values for a raster with rectangular pixels (e.g. Lat/Lon grid)
        In this case 45 deg does not pas through a straight diagonal of pixels... 
        """
        
        if angle % 90 == 0 : return angle
                    
        diag = self.pix_x / self.pix_y 
        # tangent which would be 45 deg in a normal grid
            
        tan_dir = np.tan(np.radians(angle ))            
        
        # not used, for memory
           # true_dir = np.degrees( np.arctan(
            #            dem.pix_x * abs(tan_dir)  / dem.pix_y))
                       
        
        # normally, an angle on x/y plane = arctan(x/y)
        # but with a deformation w this becomes arctan( x / (y*w) )
        # where w = x/y for theoretical 45deg, i.e. pix_x/pix_y
        direction = np.degrees(np.arctan(tan_dir / diag)) 
        if angle >= 270 : direction += 360
        elif angle >= 90: direction += 180 
  
        return direction
