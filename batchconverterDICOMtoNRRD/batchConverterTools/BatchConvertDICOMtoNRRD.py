from __future__ import print_function
from __main__ import vtk, qt, ctk, slicer

import os
import glob
import csv
import collections
from datetime import datetime

import SimpleITK as sitk
import sitkUtils as su
import dicom

from slicer.ScriptedLoadableModule import *

#from BatchRTStructConversion import BatchRTStructConversionLogic
#from DatabaseHandler import DatabaseHandler

import pdb
 

def VolumeIntensityCorrection(volume, logFilePath):
    spacing = volume.GetSpacing()
    origin = volume.GetOrigin()
    ras2ijk = vtk.vtkMatrix4x4()
    ijk2ras = vtk.vtkMatrix4x4()
    volume.GetRASToIJKMatrix(ras2ijk)
    volume.GetIJKToRASMatrix(ijk2ras)
    
    imgsitk = su.PullFromSlicer(volume.GetName())
    imgsitk_array = sitk.GetArrayFromImage(imgsitk)
    imgsitk_array = imgsitk_array.__sub__(imgsitk_array.min())
    imgsitk = sitk.GetImageFromArray(imgsitk_array)
    outputImageName = volume.GetName() + '_corrected'
    su.PushToSlicer(imgsitk, outputImageName)
    volumeCorrected = slicer.util.getNode(outputImageName)
          
    volumeCorrected.SetOrigin(origin)
    volumeCorrected.SetSpacing(spacing)
    volumeCorrected.SetRASToIJKMatrix(ras2ijk)
    volumeCorrected.SetIJKToRASMatrix(ijk2ras)
    
    with open(logFilePath,mode='a') as logfile: logfile.write("\tCORRECTED: Image intensity values corrected: " + volumeCorrected.GetName() + '\n')
    return volumeCorrected

def SaveLabelMapContours(labelMapContours, outputSegmentationsDir, fileFormat, logFilePath):    
    volumesLogic = slicer.vtkSlicerVolumesLogic()
    for labelMapContour in labelMapContours:
        volumesLogic.CenterVolume(labelMapContour)
        savenamelabel = labelMapContour.GetName()
        savenamelabel = ''.join(x for x in savenamelabel if x not in "',;\/:*?<>|") + fileFormat
        savelabel = slicer.util.saveNode(labelMapContour, os.path.join(outputSegmentationsDir, savenamelabel), properties={"filetype": fileFormat})
        if not savelabel:
            with open(logFilePath,mode='a') as logfile: logfile.write("\tSAVEERROR: Could not save data" + labelMapContour.GetName() + '\n')     
        

class BatchConverterLogic():
    def __init__(self, inputPatientDir, outputPatientDir, contourFilters, converterSettings):
        self.inputPatientDir = inputPatientDir
        self.outputPatientDir = outputPatientDir
        self.contourFilters = contourFilters
        self.converterSettings = converterSettings
        
        logTime = str(datetime.now().strftime(('%Y-%m-%d--%H-%M')))
        self.logFilePath = os.path.join(outputPatientDir, 'BatchConverterLog_' + logTime + '.txt')
        
        self.PatientDirs = [patDir for patDir in glob.glob(os.path.join(inputPatientDir, '*')) if os.path.isdir(patDir)]
        
        self.dblogic = DatabaseHandler(inputPatientDir)
        if converterSettings['convertcontours']=='All':
            self.RTStructConversionlogic = BatchRTStructConversionLogic()
            self.RTStructConversionlogic.SetContourFilters(convertAll=True)
        elif converterSettings['convertcontours']=='Select':
            self.RTStructConversionlogic = BatchRTStructConversionLogic()
            self.RTStructConversionlogic.SetContourFilters(contourFilters=contourFilters)
            
    def InitializeProgressBar(self, numDirectories):
        # initialize Progress Bar
        self.progressBar = qt.QProgressDialog(slicer.util.mainWindow())
        self.progressBar.minimumDuration = 0
        self.progressBar.show()
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(numDirectories)
  
    def UpdateProgressBar(self, patientID, index):
        self.progressBar.labelText = 'Converting DICOM Images to NRRD for patient: %s ' % patientID
        self.progressBar.setValue(index)
        slicer.app.processEvents()  
    
    def createDataHierarchy(self, patientID, studyDate, studyDescription):
        # Create Output Patient Directory
        outputPatientIDDir = str(os.path.join(self.outputPatientDir,patientID))
        if not os.path.exists(outputPatientIDDir): os.mkdir(outputPatientIDDir) 
        
        # Create Output Study Directory Within Patient Directory
        studyDateDirName = studyDate + '_' + studyDescription
        studyDateDirName = ''.join(x for x in studyDateDirName if x not in "-',;\/:*?<>|")         
        outputStudyDateDir = str(os.path.join(outputPatientIDDir,studyDateDirName))      
        if not os.path.exists(outputStudyDateDir): os.mkdir(outputStudyDateDir)
        
        # Create Reconstructions, Segmentations, and Resources Directories
        outputReconstructionsDir = os.path.join(outputStudyDateDir, 'Reconstructions')
        outputSegmentationsDir = os.path.join(outputStudyDateDir, 'Segmentations')
        outputResourcesDir = os.path.join(outputStudyDateDir, 'Resources')
        if not os.path.exists(outputReconstructionsDir): os.mkdir(outputReconstructionsDir)
        if not os.path.exists(outputSegmentationsDir): os.mkdir(outputSegmentationsDir) 
        if not os.path.exists(outputResourcesDir): os.mkdir(outputResourcesDir)

        return outputReconstructionsDir, outputSegmentationsDir, outputResourcesDir

    def saveVolumes(self, listVolumes, outputDir, islabelMap=False):
        volumesLogic = slicer.vtkSlicerVolumesLogic()
        for volume in listVolumes:
            if self.converterSettings["center"] and islabelMap:
                volumesLogic.CenterVolume(volume)
            savename = volume.GetName() 
            savename = ''.join(x for x in savename if x not in "',;\/:*?<>|") + self.converterSettings["fileformat"]       
            savevol = slicer.util.saveNode(volume, os.path.join(outputDir, savename), properties={"filetype": self.converterSettings["fileformat"]})
            if not savevol:
                with open(self.logFilePath,mode='a') as logfile: logfile.write("\tSAVEERROR: Could not save data" + volume.GetName() + '\n')        
            
    def batchConvert(self):
        self.InitializeProgressBar(len(self.PatientDirs))
        
        for index,patientDir in enumerate(self.PatientDirs):
            patientDirName = os.path.basename(patientDir) 
            self.UpdateProgressBar(patientDirName, index)              
            with open(self.logFilePath,mode='a') as logfile: logfile.write("\nPROCESSING: " + patientDirName + '\n')
            
            # Import Directory into ctkDICOMIndexer. If that fails, instantiate a new database file
            # Check if import added any new patients to the database
            try: patientsAdded = self.dblogic.ImportStudy(patientDir)
            except:
                self.dblogic.SetAndOpenNewDatabase()
                patientsAdded = self.dblogic.ImportStudy(patientDir)       
            if patientsAdded == 0:    
                with open(self.logFilePath,mode='a') as logfile: logfile.write("\tPATIENTERROR: No new patients added to database from directory: " + patientDirName + '\n')
                slicer.mrmlScene.Clear(0)
                continue

            detailsPopup = slicer.modules.dicom.widgetRepresentation().self().detailsPopup
            for patient in patientsAdded:
                try: studiesList = slicer.dicomDatabase.studiesForPatient(patient)
                except:
                    with open(self.logFilePath,mode='a') as logfile: logfile.write("\tSTUDYERROR: could not find studies for Patient: " + patientDirName + ' with DB Index: ' + patient + '\n')
                    slicer.mrmlScene.Clear(0)
                    continue
                          
                for study in studiesList:
                    try: seriesListStudy = slicer.dicomDatabase.seriesForStudy(study)
                    except:
                        with open(self.logFilePath,mode='a') as logfile: logfile.write("\tSERIESERROR: could not find Series for Study: " + study + " for Patient: " + patientDirName + '\n')
                        slicer.mrmlScene.Clear(0)
                        continue
                    
                    # Establish current patient ID
                    if self.converterSettings["inferpatientid"] == "metadata":
                        try: patientID = str(self.dblogic.GetDicomHeaderAttribute(seriesListStudy[0],'0010,0020'))
                        except: patientID = "Unknown_" + str(index) 
                    elif self.converterSettings["inferpatientid"] == "inputdir":      
                        try: patientID = patientDirName
                        except: patientID = "Unknown_" + str(index)
                    
                    # Establish current Study Date and Study Description
                    try: studyDate = self.dblogic.GetDicomHeaderAttribute(seriesListStudy[0], '0008,0020')
                    except: studyDate = "Unknown-" + str(datetime.now().strftime(('%Y-%m-%d--%H-%M')))
                    try: studyDescription = self.dblogic.GetDicomHeaderAttribute(seriesListStudy[0], '0008,1030')
                    except: studyDescription = "Unknown"    

                    # Create Data Directory Hierarchy in output directory
                    reconstructionsDir, segmentationsDir, resourcesDir = self.createDataHierarchy(patientID, studyDate, studyDescription)
                    
                    """
                    ###BRAINLAB####
                    # within a timepoint/studydate, manually defining pre-op and post-op images based on series date
                    lstdates = {}
                    for volume in listVolumes:
                      if 'FLAIR' not in volume.GetName().upper():           
                        seriesDate = dblogic.GetDicomHeaderAttributeLoaded(volume,'0008,0021')
                        lstdates[seriesDate] = volume
                    if min(lstdates.keys()) != max(lstdates.keys()):
                      if '_preop' not in lstdates[min(lstdates.keys())].GetName():          
                        lstdates[min(lstdates.keys())].SetName( lstdates[min(lstdates.keys())].GetName() + '_preop' )
                      if '_postop' not in lstdates[max(lstdates.keys())].GetName():  
                        lstdates[max(lstdates.keys())].SetName( lstdates[max(lstdates.keys())].GetName() + '_postop' )
                    else:
                      contourNodes = slicer.util.getNodes('vtkMRMLContourNode*').values()
                      for contourNode in contourNodes.values():
                        if 'POST' in contourNode.GetName().upper():
                          if '_preop' not in lstdates[min(lstdates.keys())].GetName(): 
                            lstdates[max(lstdates.keys())].SetName( lstdates[max(lstdates.keys())].GetName() + '_postop' )
                        else:
                          if '_postop' not in lstdates[max(lstdates.keys())].GetName():
                            lstdates[min(lstdates.keys())].SetName( lstdates[min(lstdates.keys())].GetName() + '_preop' )
                    ################ 
                    """
                    
                    # Load Images from Study into Slicer
                    listVolumes = []
                    listVolumes = self.dblogic.LoadPatientsIntoSlicer(study)

                    # Load contours into slicer and convert to label maps if specified by user
                    listLabelMapContours = []                    
                    if (self.converterSettings['convertcontours'] != 'None') or (len(self.contourFilters) != 0):
                        # Get label map contours         
                        listLabelMapContours = self.RTStructConversionlogic.ConvertContoursToLabelmap(listVolumes, self.logFilePath)                  

                    # Save images as NRRD    
                    if listVolumes: 
                        # Perform intensity correction on images and save them         
                        # listVolumes = [VolumeIntensityCorrection(volume, logFilePath=logFilePath) if volume.GetImageData().GetScalarRange()[0] > 32000.0 else volume for volume in listVolumes]      
                        self.saveVolumes(listVolumes, reconstructionsDir)  
                    else:
                        with open(self.logFilePath, mode='a') as logfile: logfile.write("\tIMAGEERROR: could not Parse Images: " + patientDirName + ', study: ' + studyDate + '\n')
                    
                    # Save label maps as NRRD 
                    if len(listLabelMapContours) > 0:                 
                        self.saveVolumes(listLabelMapContours, segmentationsDir, isLabelMap=True)            
                    else:
                        with open(self.logFilePath,mode='a') as logfile: logfile.write("\tRTSTRUCTERROR: could not Parse RTSTRUCTs: " + patientDirName + ', study: ' + studyDate + '\n')  
                    
                    # Clear data within Slicer
                    slicer.mrmlScene.Clear(0)
                slicer.mrmlScene.Clear(0)    
            slicer.mrmlScene.Clear(0)         
        slicer.mrmlScene.Clear(0)
        self.progressBar.close()
        self.progressBar = None
    
class BatchRTStructConversionLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        self.convertAll = True
        
    def SetContourFilters(self, contourFilters=None, convertAll=False):
        if convertAll:
            self.convertAll = True
            self.contourFilters = None
        else:
            self.convertAll = False
            self.contourFilters = contourFilters
        
    def ConvertContoursToLabelmap(self, listVolumes, logFilePath):
        import vtkSlicerContoursModuleLogic
        
        referenceVolume = None 
        labelmapsToSave = []
        
        contourNodes = slicer.util.getNodes('vtkMRMLContourNode*')
        if not contourNodes: return None
        
        for contourNode in contourNodes.values():
            if self.convertAll:
                contourFilter = {'Name': None}
            else:
                contourFilter = self.TestContourNode(contourNode.GetName(), self.contourFilters )
                
            if contourFilter:
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

                # Resample and Center Label Map
                #if referenceVolume.GetSpacing() != contourLabelmapNode.GetSpacing():
                #    self.ResampleScalarVolumeCLI(referenceVolume, contourLabelmapNode)
                #    with open(logFilePath,mode='a') as logfile:logfile.write("\tRESAMPLED: Label Resampled to Image and Centered: " + contourLabelmapNode.GetName() + '\n')
                
                # Binarize Label Map
                #contourLabelmapNode = self.BinarizeLabelMap(contourLabelmapNode, logFilePath)
                
                # Append contour to list
                labelmapsToSave.append(contourLabelmapNode)
        return labelmapsToSave
        
    def TestContourNode(self, contourName, contourFilters):
        contourName = contourName.upper()
        filterSuccess = False
        for contourFilter in contourFilters:
            if len(contourFilter['Include']) == 0:
                if len(contourFilter['Exclude']) == 0:
                    filterSuccess = contourFilter
                    break
                else:
                    if (not any(substring.upper() in contourName for substring in contourFilter['Exclude'])):
                        filterSuccess = contourFilter
                        break
            else: 
                if len(contourFilter['Exclude']) == 0:
                    if (all(substring.upper() in contourName for substring in contourFilter['Include'])):
                        filterSuccess = contourFilter
                        break                        
                else:
                    if (all(substring.upper() in contourName for substring in contourFilter['Include']) and (not any(substring.upper() in contourName for substring in contourFilter['Exclude']))):
                        filterSuccess = contourFilter
                        break                      
        return filterSuccess 
        
    def ResampleScalarVolumeCLI(self, image, label):
        outputSpacing = image.GetSpacing()
        parameters = {}
        parameters["InputVolume"] = label
        parameters["OutputVolume"] = label
        parameters["outputPixelSpacing"] = ','.join(str(val) for val in outputSpacing)
    
        resamplevolume = slicer.modules.resamplescalarvolume 
        return (slicer.cli.run(resamplevolume, None, parameters, wait_for_completion = True))
              
    def BinarizeLabelMap(self, labelNode, logFilePath):
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

        
class DatabaseHandler():   
    def __init__(self, inputPatientDir):
        self.databases = {}
        self.dbDir = os.path.join(inputPatientDir,'DatabaseDirectory')
        self.dbCounter = 0
        
        if not os.path.exists(self.dbDir): os.mkdir(self.dbDir)
        self.SetAndOpenNewDatabase()
        
    def SetAndOpenNewDatabase(self):
        self.dbCounter += 1
    
        self.databases[self.dbCounter] = {}
        self.databases[self.dbCounter]['NumberPatients'] = 0
        self.databases[self.dbCounter]['FilePath'] = os.path.join(self.dbDir, 'Round'+str(self.dbCounter)+'DB')     
        self.dicomDatabaseDir = self.databases[self.dbCounter]['FilePath']
        
        dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
        dicomWidget.onDatabaseDirectoryChanged(self.dicomDatabaseDir)
        #slicer.dicomDatabase.initializeDatabase()
        
    def ImportStudy(self, dicomDataDir):
        indexer = ctk.ctkDICOMIndexer()
        # Import study to database
        indexer.addDirectory( slicer.dicomDatabase, dicomDataDir )
        indexer.waitForImportFinished()
        
        # Check if import added any new patients to the database
        if len(slicer.dicomDatabase.patients()) > self.databases[self.dbCounter]['NumberPatients']:     
            patientsAdded = slicer.dicomDatabase.patients()[self.databases[self.dbCounter]['NumberPatients']:]
            self.databases[self.dbCounter]['NumberPatients'] = len(slicer.dicomDatabase.patients())
            return patientsAdded
        else:
            return 0
          
    def LoadPatientsIntoSlicer(self, study):
        # Choose first patient from the patient list
        detailsPopup = slicer.modules.dicom.widgetRepresentation().self().detailsPopup
        series = [slicer.dicomDatabase.seriesForStudy(study)]
        seriesUIDs = [uid for uidList in series for uid in uidList]
        
        detailsPopup.offerLoadables(seriesUIDs, 'SeriesUIDList')
        detailsPopup.examineForLoading()
    
        loadables = detailsPopup.loadableTable.loadables
    
        # Load into Slicer
        detailsPopup = slicer.modules.dicom.widgetRepresentation().self().detailsPopup
        detailsPopup.loadCheckedLoadables()
             
        listVolumes = slicer.util.getNodes('vtkMRMLScalarVolumeNode*').values()
        return listVolumes
        
    def GetDicomHeaderAttribute(self, series, tag):
        fileName = slicer.dicomDatabase.filesForSeries(series)[0]
        attribute = slicer.dicomDatabase.fileValue(fileName,tag)  
        return attribute
      
    def GetDicomHeaderAttributeLoaded(self, volume, tag):
        instUids = volume.GetAttribute('DICOM.instanceUIDs').split()
        filename = slicer.dicomDatabase.fileForInstance(instUids[0])
        attribute = str(slicer.dicomDatabase.fileValue(filename,tag)) 
        return attribute  
     
      
    