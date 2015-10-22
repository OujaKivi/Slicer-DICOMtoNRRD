from __future__ import print_function
from __main__ import vtk, qt, ctk, slicer

import SimpleITK as sitk
import sitkUtils as su
import os
import glob

import dicom
import csv
import collections

import pdb

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
  
   