# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 12:07:10 2020

@author: zcuckovi
"""
import numpy as np



def view (offset_y, offset_x, shape, step=1, edge=0):
    """            
    Function returning two matching numpy views for moving window routines.
    - offset_y and offset_x refer to the shift in relation to the analysed (central) cell 
    - size_y and size_x refer to the size of the data matrix (not of the window!)
    - view_in is the shifted view and view_out is the position of central cells
    """
    size_y, size_x = shape

    size_y -= edge; size_x -= edge
     
    x = abs(offset_x) 
    y = abs(offset_y) 
 
    x_in = slice(x + edge , size_x, step) 
    x_out = slice(edge, size_x - x, step)

 
    y_in = slice(y + edge, size_y, step)
    y_out = slice(edge, size_y - y, step)
 
    # the swapping trick    
    if offset_x < 0: x_in, x_out = x_out, x_in                                 
    if offset_y < 0: y_in, y_out = y_out, y_in
 
    # return window view (in) and main view (out)
    return np.s_[y_in, x_in], np.s_[y_out, x_out]


def window_loop (shape, chunk, axis = 0, reverse = False, overlap = 0):
            """
            Construct a frame to extract chunks of data from gdal
            (and to insert them properly to a numpy matrix)
            """
            xsize, ysize = shape if axis==0 else shape[::-1]

            if reverse :
                steps = np.arange(xsize // chunk, -1, -1 )
                begin = xsize
            else: 
                steps = np.arange(1, xsize // chunk +2 )
                begin =0

            x, y, x_off, y_off = 0,0, xsize, ysize

            for step in steps:

                end = min(int(chunk * step), xsize)
                
                if reverse :  x, x_off = end, begin - end
                else:         x, x_off = begin, end - begin

                begin = end
                
               # ov = overlap * int(step)
                ov = overlap

                ov_left = ov if x > ov else x
                ov_right = ov if (x + x_off + ov < xsize) else (xsize -(x + x_off))

                x_in = x - ov_left
                #this is an offset from x_in !!, not coords
                x_in_off = x_off + ov_right + ov_left

               
                if not axis : gdal_take =(x_in, y, x_in_off, y_off)
                else: gdal_take = (y, x_in, y_off, x_in_off)
              
                    #AXIS SWAP : cannot be handled as transposition,
                    # we need precise coords for GDAL
                in_view = np.s_[:,: x_in_off] if not axis else np.s_[: x_in_off, :]

                x_out = x if ov_left == ov else 0

                x_out_off = x_off + (ov_left if ov_left < ov else 0) + (ov_right if ov_right < ov else 0) 

                if not axis : gdal_put =(x_out, y, x_out_off, y_off)
                else: gdal_put = (y, x_out, y_off, x_out_off)
                
                #todo !! off nije isti za view i za GDAL !!
                sx = slice(0 if ov_left < ov else ov , x_out_off + ov_left + (ov_right if ov_right < ov else 0))

                out_view = np.s_[:, sx] if not axis else np.s_[sx , :]
          
                yield in_view, gdal_take, out_view, gdal_put
                
                
def filter3 (raster, average=True):
    """ A basic smooth filter in 3x3 window """ 
    temp_matrix = np.zeros(raster.shape)
    
    for i in range(-1,2):
        for j in range(-1,2):
            view_in, view_out = view(i , j ,raster.shape)
            temp_matrix[view_out] += raster[view_in]
                    
    if average: temp_matrix /= 9
    return temp_matrix
