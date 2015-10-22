from __main__ import vtk, qt, ctk, slicer, os

import batchConverterTools

#
# DICOM to NRRD Batch Converter module
#

class batchConverter:
    def __init__(self, parent):  
        parent.title = "DICOMtoNRRDBatchConverter"
        parent.categories = ["Converters"]
        parent.contributors = ["Vivek Narayan / Hugo Aerts"]
        parent.helpText = """
        Use this module to convert DICOM files to NRRD images in the following Data Hierarchy:
        --Dataset
            --PatientID
                --StudyDate_StudyDescription
                   --Reconstructions
                   --Resources
                   --Segmentations
        """
        parent.acknowledgementText = """ This module was created at Dana Farber Cancer Institute""" 
        self.parent = parent

#
# Widget
#

class batchConverterWidget:
    def __init__(self, parent=None):
        if not parent:
            self.parent = slicer.qMRMLWidget()
            self.parent.setLayout(qt.QVBoxLayout())
            self.parent.setMRMLScene(slicer.mrmlScene)
        else:
            self.parent = parent
        self.layout = self.parent.layout()
        if not parent:
            self.setup()
            self.parent.show()
    
        self.inputPatientDir = self.outputPatientDir = {}
      
    def setup(self):
        #---------------------------------------------------------
        # Batch Covert DICOM to NRRD
        self.BatchConvertCollapsibleButton = ctk.ctkCollapsibleButton()
        self.BatchConvertCollapsibleButton.text = "Batch convert DICOM to NRRD or NIFTI"
        self.layout.addWidget(self.BatchConvertCollapsibleButton)
        self.BatchConvertCollapsibleButton.collapsed = False 
        self.BatchConvertFormLayout = qt.QFormLayout(self.BatchConvertCollapsibleButton)
    
        # Input 1: Input Directory selector
        self.input1Frame = qt.QFrame(self.BatchConvertCollapsibleButton)
        self.input1Frame.setLayout(qt.QHBoxLayout())
        self.BatchConvertFormLayout.addWidget(self.input1Frame)
        
        self.input1Selector = qt.QLabel("Input Directory (DICOM):  ", self.input1Frame)
        self.input1Frame.layout().addWidget(self.input1Selector)
        self.input1Button = qt.QPushButton("Select main directory DICOM files")
        self.input1Button.toolTip = "Select main directory with DICOM files (folder names are patient names)"
        self.input1Button.enabled = True
        self.input1Frame.layout().addWidget(self.input1Button)
    
        # Input 2: Output Directory selector
        self.input2Frame = qt.QFrame(self.BatchConvertCollapsibleButton)
        self.input2Frame.setLayout(qt.QHBoxLayout())
        self.BatchConvertFormLayout.addWidget(self.input2Frame)
        
        self.input2Selector = qt.QLabel("Output Directory:  ", self.input2Frame)
        self.input2Frame.layout().addWidget(self.input2Selector)
        self.input2Button = qt.QPushButton("Select main directory output NRRD or NFITI files")
        self.input2Button.toolTip = "Select main directory for output NRRD or NIFTI files (folder names are patient names)"
        self.input2Button.enabled = True
        self.input2Frame.layout().addWidget(self.input2Button)
    
        # NRRD or NIFTI Radio Buttons
        self.fileFormatFrame = qt.QFrame(self.BatchConvertCollapsibleButton)
        self.fileFormatFrame.setLayout(qt.QHBoxLayout())
        self.BatchConvertFormLayout.addWidget(self.fileFormatFrame)
        
        self.fileFormatSelector = qt.QLabel("Output File Format:  ", self.fileFormatFrame)
        
        self.radioButtonFrame = qt.QFrame(self.fileFormatFrame)
        self.radioButtonFrame.setLayout(qt.QFormLayout())
        self.fileFormatGroup = qt.QButtonGroup(self.fileFormatFrame)
        self.nrrdButton = qt.QRadioButton("NRRD")
        self.nrrdButton.checked = True
        self.niftiButton = qt.QRadioButton("NIFTI")
        self.fileFormatGroup.addButton(self.nrrdButton)
        self.fileFormatGroup.addButton(self.niftiButton)
        self.radioButtonFrame.layout().addRow(self.nrrdButton, self.niftiButton)
        
        self.fileFormatFrame.layout().addWidget(self.fileFormatSelector)
        self.fileFormatFrame.layout().addWidget(self.radioButtonFrame)
        
        # Parse and Save DICOM Metadata to CSV
        self.metadataExtractFrame = qt.QFrame(self.BatchConvertCollapsibleButton)
        self.metadataExtractFrame.setLayout(qt.QFormLayout())        
        self.metadataExtract = qt.QCheckBox("Extract DICOM Metadata", self.metadataExtractFrame)
        self.metadataExtract.toolTip = "Extract and Save all DICOM Metadata to a CSV file"
        self.metadataExtract.checked = True
        self.metadataExtractFrame.layout().addRow(self.metadataExtract)
        self.BatchConvertFormLayout.addWidget(self.metadataExtractFrame)
        
        # Apply Batch Convert button
        self.applyBatchButton = qt.QPushButton("Apply Batch Convert", self.BatchConvertCollapsibleButton)
        self.applyBatchButton.toolTip = "Batch convert DICOM to NRRD or NIFTI files" 
        self.BatchConvertFormLayout.addWidget(self.applyBatchButton)
        self.applyBatchButton.enabled = False
        
        #---------------------------------------------------------
        # Connections
        self.input1Button.connect('clicked(bool)', self.onInput1Button)
        self.input2Button.connect('clicked(bool)', self.onInput2Button)
        self.applyBatchButton.connect('clicked(bool)', self.onBatchApply) 
    
  
    def onInput1Button(self):
        self.inputPatientDir = qt.QFileDialog.getExistingDirectory()
        self.input1Button.text = self.inputPatientDir
        if self.inputPatientDir and self.outputPatientDir: self.applyBatchButton.enabled = True
    
    def onInput2Button(self):
        self.outputPatientDir = qt.QFileDialog.getExistingDirectory()
        self.input2Button.text = self.outputPatientDir
        if self.inputPatientDir and self.outputPatientDir: self.applyBatchButton.enabled = True
     
    def onBatchApply(self):
        self.applyBatchButton.enabled = False
        if self.nrrdButton.checked is True: self.fileFormat=".nrrd"
        else: self.fileFormat=".nii"
        
        batchConverterTools.BatchConvertDICOMtoNRRD.batchConvert(self.inputPatientDir, self.outputPatientDir, self.fileFormat)
        
        if self.metadataExtract.checked:
            DicomHeaderParserInstance = batchConverterTools.MetadataExtractor.DicomHeaderParser(self.inputPatientDir)
            DicomHeaderParserInstance.ExecuteDicomHeaderParser()
            DicomHeaderParserInstance.WriteToCSVFile(outputDir=self.outputPatientDir)        
            
        self.applyBatchButton.enabled = True
        self.applyBatchButton.text = "Apply Batch Convert"