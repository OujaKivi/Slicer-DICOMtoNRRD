from __future__ import print_function

from __main__ import vtk, qt, ctk, slicer
import os

import pdb
from slicer.ScriptedLoadableModule import *
    
class BatchRTStructConversionLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
  
    def ConvertContoursToLabelmap(self, listVolumes, logFilePath):
        import vtkSlicerContoursModuleLogic
        
        referenceVolume = None 
        labelmapsToSave = []
        
        contourNodes = slicer.util.getNodes('vtkMRMLContourNode*')
        if not contourNodes: return None
        
        for contourNode in contourNodes.values():
            # Can check for specific contour here i.e. if 'TUMOR' in contourNode.GetName().upper():
            # if 'GTV' in contourNode.GetName().upper() and '+' not in contourNode.GetName():
            if contourNode:
                with open(logFilePath,mode='a') as logfile: logfile.write('\tCONVERTING: Contour: ' + contourNode.GetName() + '\n')
                
                # Set referenced volume as rasterization reference 
                referenceVolume = vtkSlicerContoursModuleLogic.vtkSlicerContoursModuleLogic.GetReferencedVolumeByDicomForContour(contourNode)
                
                """
                # manually set reference volume
                for vol in listVolumes:
                  if 'FLAIR' in contourNode.GetName().upper():
                    if 'FLAIR' in vol.GetName().upper():
                      referenceVolume = vol
                  else:
                    if 'FLAIR' not in vol.GetName().upper():
                      referenceVolume = vol
                """
                
                if not referenceVolume:
                    with open(logFilePath,mode='a') as logfile: logfile.write('\tREFERENCEERROR: No reference volume found for contour: ' + contourNode.GetName() + '\n')
                    continue
                  
                contourNode.SetAndObserveRasterizationReferenceVolumeNodeId(referenceVolume.GetID())
                with open(logFilePath,mode='a') as logfile: logfile.write("\tREFERENCED: Label: " + contourNode.GetName() + ' Reference: ' + referenceVolume.GetName() + '\n')
                
                # Perform conversion
                contourNode.GetLabelmapImageData()
                contourLabelmapNode = vtkSlicerContoursModuleLogic.vtkSlicerContoursModuleLogic.ExtractLabelmapFromContour(contourNode)
                contourLabelmapNode.SetName(referenceVolume.GetName() + '_' + contourLabelmapNode.GetName())
                
                #Resample and Center Label Map
                if referenceVolume.GetSpacing() != contourLabelmapNode.GetSpacing():
                    self.ResampleScalarVolumeCLI(referenceVolume, contourLabelmapNode)
                    with open(logFilePath,mode='a') as logfile:logfile.write("\tRESAMPLED: Label Resampled to Image and Centered: " + contourLabelmapNode.GetName() + '\n')
                    
                # Append contour to list
                labelmapsToSave.append(contourLabelmapNode)
        return labelmapsToSave
    
    def ResampleScalarVolumeCLI(self, image, label):
        outputSpacing = image.GetSpacing()
        parameters = {}
        parameters["InputVolume"] = label
        parameters["OutputVolume"] = label
        parameters["outputPixelSpacing"] = ','.join(str(val) for val in outputSpacing)
    
        resamplevolume = slicer.modules.resamplescalarvolume 
        return (slicer.cli.run(resamplevolume, None, parameters, wait_for_completion = True))
              
    def SaveLabelMapContours(self, labelMapContours, outputSegmentationsDir, fileFormat, logFilePath):    
        volumesLogic = slicer.vtkSlicerVolumesLogic()
        for labelMapContour in labelMapContours:
            labelMapContour = logic.binarizeLabelMap(labelMapContour, logFilePath)
            volumesLogic.CenterVolume(labelMapContour)
            savenamelabel = labelMapContour.GetName()
            savenamelabel = ''.join(x for x in savenamelabel if x not in "',;\/:*?<>|") + fileFormat
            savelabel = slicer.util.saveNode(labelMapContour, os.path.join(outputSegmentationsDir, savenamelabel), properties={"filetype": fileFormat})
            if not savelabel:
                with open(logFilePath,mode='a') as logfile: logfile.write("\tSAVEERROR: Could not save data" + labelMapContour.GetName() + '\n')     
            
    def binarizeLabelMap(self, labelNode, logFilePath):
        labelNodeImageData = labelNode.GetImageData()
        change = slicer.vtkImageLabelChange()
        change.SetInputData(labelNodeImageData)
        change.SetOutput(labelNodeImageData)
        change.SetOutputLabel(1)
        
        for i in xrange(1,int(labelNodeImageData.GetScalarRange()[1])+1):
            change.SetInputLabel(i)
            change.Update()
            
        labelNode.SetAndObserveImageData(labelNodeImageData)
        with open(logFilePath,mode='a') as logfile: logfile.write("\tBINARIZED: LabelMap Binarized: " + labelNode.GetName() + '\n')
          
        return labelNode
      
  
     
      
