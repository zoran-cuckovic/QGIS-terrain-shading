# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 12:07:10 2020

@author: zcuckovi
"""
import numpy as np

from typing import List
import math



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


def window_loop (shape, chunk, 
                 axis = 0, reverse = False, overlap = 0, offset = 0):
            """
            Construct a frame to extract chunks of data from gdal
            (and to insert them properly to a numpy matrix)
            """
            xsize, ysize = shape if axis == 0 else shape[::-1]
                        
            if reverse : 
                begin, step, stride = xsize, 1 + xsize // chunk, -1
            else: 
                begin, step, stride = 0, 0, 1

            x, y, x_off, y_off = 0,0, xsize, ysize
            
            end = 1
            
            while xsize > end > 0 : 
           
                step += stride

                end = min(int(chunk * step), xsize)
                
                if reverse :  x, x_off = end, begin - end
                else:         x, x_off = begin, end - begin
                
                # move window front or back, which means only one margin will overlap
                if (offset < 0 and x >= abs(offset)) or (
                    offset > 0 and x <= xsize-offset) : 
                    x += offset * int(step)
                
                begin = end
                
               # ov = overlap * int(step)
                ov = overlap

                ov_left = min(ov, x) # do not spill over the border
                ov_right = min (ov, (xsize - (x + x_off)))

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
                
                sx = slice(0 if ov_left < ov else ov , 
                           x_out_off + ov_left + (ov_right if ov_right < ov else 0))

                out_view = np.s_[:, sx] if not axis else np.s_[sx , :]
          
                yield in_view, gdal_take, out_view, gdal_put


# ======= TODO : a class to handle filtering ==============
#class Convolve:
#               - 3x3 filter
#               - hillshade filters
#               - tpi filters
#               - ? occlusion directed filter
                
def filter3 (raster, mode='average'):
    """
    A pply a 3x3 filter.
    Modes : simple, average, laplacian
    """
    average = mode == 'average'
    laplace = mode == 'laplacian'
    
    temp_matrix = np.zeros(raster.shape)
    
    if average : 
        temp_count = np.zeros(raster.shape)
        # set borders first  
        temp_count[:]= 6
        # main area : 9 points to test 
        temp_count[1:-1, 1:-1] = 9
        # corners
        for v in [(0,0),(-1,-1),(0,-1), (-1,0)]: temp_count[v] = 4
                          
    
    for i in range(-1,2):
        for j in range(-1,2):
            view_in, view_out = view(i , j ,raster.shape)
            
            z= raster[view_in]
            if laplace and i==0 and j==0: 
                z = z * -8  # this is a view, do not *=
            temp_matrix[view_out] += z        
                    
    if average: temp_matrix /= temp_count
    return temp_matrix


# Code from : https://github.com/fasiha/nextprod-py
def nextpow(a: float, x: float) -> float:
  """The smallest `a^n` not less than `x`, where `n` is a non-negative integer.
  
  `a` must be greater than 1, and `x` must be greater than 0.
  # Examples
  ```jldoctest
  julia> nextpow(2, 7)
  8
  julia> nextpow(2, 9)
  16
  julia> nextpow(5, 20)
  25
  julia> nextpow(4, 16)
  16
  ```
  """
  assert x > 0 and a > 1
  if x <= 1:
    return 1.0
  n = math.ceil(math.log(x, a))
  p = a**(n - 1)
  return p if p >= x else a**n


# Code from : https://github.com/fasiha/nextprod-py
def nextprod(a: List[int], x: int) -> int:
  """Next integer greater than or equal to `x` that can be written as ``\\prod k_i^{a_i}`` for integers
  ``a_1``, ``a_2``, etc.
  # Examples
  ```jldoctest
  julia> nextprod([2, 3], 105)
  108
  julia> 2^2 * 3^3
  108
  ```
  """
  k = len(a)
  v = [1] * k  # current value of each counter
  mx = [nextpow(ai, x) for ai in a]  # maximum value of each counter
  v[0] = mx[0]  # start at first case that is >= x
  p = mx[0]  # initial value of product in this case
  best = p
  icarry = 1

  while v[-1] < mx[-1]:
    if p >= x:
      best = p if p < best else best  # keep the best found yet
      carrytest = True
      while carrytest:
        p = p // v[icarry - 1]
        v[icarry - 1] = 1
        icarry += 1
        p *= a[icarry - 1]
        v[icarry - 1] *= a[icarry - 1]
        carrytest = v[icarry - 1] > mx[icarry - 1] and icarry < k
      if p < x:
        icarry = 1
    else:
      while p < x:
        p *= a[0]
        v[0] *= a[0]
  return int(mx[-1] if mx[-1] < best else best)


