# -*- coding: utf-8 -*-
"""
Created on Thu Sep 17 14:12:12 2015

@author: Vivek Narayan
"""

import os
import matplotlib.pyplot as plt
import numpy
import SimpleITK as sitk


def sitk_show(img, title=None, margin=0.05, dpi=40 ):
    nda = sitk.GetArrayFromImage(img)
    spacing = img.GetSpacing()
    figsize = (1 + margin) * nda.shape[0] / dpi, (1 + margin) * nda.shape[1] / dpi
    extent = (0, nda.shape[1]*spacing[1], nda.shape[0]*spacing[0], 0)
    fig = plt.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_axes([margin, margin, 1 - 2*margin, 1 - 2*margin])

    plt.set_cmap("gray")
    ax.imshow(nda,extent=extent,interpolation=None)
    
    if title:
        plt.title(title)
    
    plt.show()
    
def main():
    # create test directory of nrrd images to process with simpleitk
    # processing tasks: 
    #   resampling to standard pixelspacing
    #   binarizing label maps,
    #   applying a filter
    # https://pyscience.wordpress.com/2014/10/19/image-segmentation-with-python-and-simpleitk/

    imagepath = ""  
    image = sitk.ReadImage(imagepath)
    
    #sitk.Show(image)
    
    imageSlice = image[:,:,15]
    sitk_show(imageSlice)

if __name__ == "__main__":
    main()