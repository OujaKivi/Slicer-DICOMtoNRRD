"""
Slicer.exe --no-splash --no-main-window --show-python-interactor --python-script "E:/Users/vn061/Desktop/DICOMtoNRRD-BatchConverter-master/commandline_script.py"
"""
import slicer
import os, sys

rbc = slicer.modules.batchconverter
rbc.createNewWidgetRepresentation()
rbcwidget = slicer.modules.batchConverterWidget

rbcwidget.__init__()

