from __main__ import vtk, qt, ctk, slicer, os

import batchConverterTools

#
# DICOM to NRRD Batch Converter module
#

class batchConverter:
    def __init__(self, parent):  
        parent.title = "DICOMBatchConverter"
        parent.categories = ["Converters"]
        parent.contributors = ["Vivek Narayan / Hugo Aerts"]
        parent.helpText = """
        This Module requires Slicer 4.4 and the DICOM-RT module installed.
        Use this module to convert DICOM/DICOM-RT files to NRRD images/label-maps in the following Data Hierarchy:
        --Dataset
            --PatientID
                --StudyDate_StudyDescription
                   --Reconstructions (Images)
                   --Resources
                   --Segmentations (Label-maps)
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
        self.reloadButton = qt.QPushButton("Reload")
        self.reloadButton.toolTip = "Reload this module."
        self.reloadButton.name = "Radiomics Reload"
        self.layout.addWidget(self.reloadButton)
        self.reloadButton.connect('clicked()', self.onReload)
    
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
        self.input1Button = qt.QPushButton("Select Main Input Directory of DICOM files")
        self.input1Button.toolTip = "Select main directory with DICOM files (folder names are patient names)"
        self.input1Button.enabled = True
        self.input1Frame.layout().addWidget(self.input1Button)
    
        # Input 2: Output Directory selector
        self.input2Frame = qt.QFrame(self.BatchConvertCollapsibleButton)
        self.input2Frame.setLayout(qt.QHBoxLayout())
        self.BatchConvertFormLayout.addWidget(self.input2Frame)
        
        self.input2Selector = qt.QLabel("Output Directory:  ", self.input2Frame)
        self.input2Frame.layout().addWidget(self.input2Selector)
        self.input2Button = qt.QPushButton("Select Main Output Directory")
        self.input2Button.toolTip = "Select main directory for output NRRD or NIFTI files (folder names are patient names)"
        self.input2Button.enabled = True
        self.input2Frame.layout().addWidget(self.input2Button)
    
        # Keywords to catch RTStruct Structures
        self.contoursFrame = qt.QFrame(self.BatchConvertCollapsibleButton)
        self.contoursFrame.setLayout(qt.QVBoxLayout())
        self.contoursFrame.setFrameStyle(2)
        self.BatchConvertFormLayout.addWidget(self.contoursFrame)
        
        self.addContourButton = qt.QPushButton("Add Contour to convert from RTStruct (separate keywords by comma)", self.contoursFrame)      
        self.keywordsScrollWidget = qt.QWidget()        
        self.keywordsScrollWidget.setLayout(qt.QFormLayout())        
        self.keywordsScroll = qt.QScrollArea()
        self.keywordsScroll.setWidgetResizable(True)
        self.keywordsScroll.setWidget(self.keywordsScrollWidget)        
        self.contoursFrame.layout().addWidget(self.keywordsScroll)
        self.contoursFrame.layout().addWidget(self.addContourButton) 
                      
        # Settings Collapsible Button
        self.settingsCollapsibleButton = ctk.ctkCollapsibleButton(self.BatchConvertCollapsibleButton)
        self.settingsCollapsibleButton.text = "Settings"
        self.settingsCollapsibleButton.setLayout(qt.QFormLayout())     
        self.BatchConvertFormLayout.addWidget(self.settingsCollapsibleButton)
        
        # NRRD or NIFTI Radio Buttons
        self.fileFormatLabel = qt.QLabel("Output File Format:  ", self.settingsCollapsibleButton)
        
        self.fileFormatSelectFrame = qt.QFrame(self.settingsCollapsibleButton)
        self.fileFormatSelectFrame.setLayout(qt.QFormLayout())
        self.fileFormatGroup = qt.QButtonGroup(self.fileFormatSelectFrame)
        self.nrrdButton = qt.QRadioButton("NRRD")
        self.nrrdButton.checked = True
        self.niftiButton = qt.QRadioButton("NIFTI")
        self.fileFormatGroup.addButton(self.nrrdButton)
        self.fileFormatGroup.addButton(self.niftiButton)
        self.fileFormatSelectFrame.layout().addRow(self.nrrdButton, self.niftiButton)        
        self.settingsCollapsibleButton.layout().addRow(self.fileFormatLabel, self.fileFormatSelectFrame)
        
        # Parse and Save DICOM Metadata to CSV
        self.metadataExtractLabel = qt.QLabel("DICOM Metadata Extraction", self.settingsCollapsibleButton)
        self.metadataExtractLabel.toolTip = "Extract and Save all DICOM Metadata to a CSV file"
        
        self.metadataExtractSelecttFrame = qt.QFrame(self.settingsCollapsibleButton)
        self.metadataExtractSelecttFrame.setLayout(qt.QFormLayout())                
        self.metadataExtractGroup = qt.QButtonGroup(self.metadataExtractSelecttFrame)
        self.extractCSVButton = qt.QRadioButton("CSV")
        self.extractCSVButton.checked = True
        #self.extractJSONButton = qt.QRadioButton("JSON")        
        self.doNotExtractButton = qt.QRadioButton("None")
        self.metadataExtractGroup.addButton(self.extractCSVButton)
        self.metadataExtractGroup.addButton(self.doNotExtractButton)
        self.metadataExtractSelecttFrame.layout().addRow(self.extractCSVButton, self.doNotExtractButton)       
        self.settingsCollapsibleButton.layout().addRow(self.metadataExtractLabel, self.metadataExtractSelecttFrame)
        
        # Use input DICOM Patient Directory names as PatientID or infer from DICOM Metadata
        self.patientIDLabel = qt.QLabel("Infer Patient IDs from:  ", self.settingsCollapsibleButton)
        self.patientIDLabel.toolTip = "Use input DICOM Patient Directory names as PatientID or infer from DICOM Metadata"
        
        self.patientIDSelectFrame = qt.QFrame(self.settingsCollapsibleButton)
        self.patientIDSelectFrame.setLayout(qt.QFormLayout())
        self.patientIDGroup = qt.QButtonGroup(self.patientIDSelectFrame)
        self.metadataButton = qt.QRadioButton("Series DICOM Metadata")
        self.metadataButton.checked = True
        self.inputDirButton = qt.QRadioButton("Input Patient Subdirectories")
        self.patientIDGroup.addButton(self.metadataButton)
        self.patientIDGroup.addButton(self.inputDirButton )
        self.patientIDSelectFrame.layout().addRow(self.metadataButton, self.inputDirButton)        
        self.settingsCollapsibleButton.layout().addRow(self.patientIDLabel, self.patientIDSelectFrame)
              
        # Apply Batch Convert button
        self.applyBatchButton = qt.QPushButton("Apply Batch Convert", self.BatchConvertCollapsibleButton)
        self.applyBatchButton.toolTip = "Batch convert DICOM to NRRD or NIFTI files" 
        self.BatchConvertFormLayout.addWidget(self.applyBatchButton)
        self.applyBatchButton.enabled = False
        
        #---------------------------------------------------------
        # Connections
        self.input1Button.connect('clicked(bool)', self.onInput1Button)
        self.input2Button.connect('clicked(bool)', self.onInput2Button)
        self.addContourButton.connect('clicked(bool)', self.addContourFilterWidget)
        self.applyBatchButton.connect('clicked(bool)', self.onBatchApply) 
    
  
    def onInput1Button(self):
        self.inputPatientDir = qt.QFileDialog.getExistingDirectory()
        self.input1Button.text = self.inputPatientDir
        if self.inputPatientDir and self.outputPatientDir: self.applyBatchButton.enabled = True
    
    def onInput2Button(self):
        self.outputPatientDir = qt.QFileDialog.getExistingDirectory()
        self.input2Button.text = self.outputPatientDir
        if self.inputPatientDir and self.outputPatientDir: self.applyBatchButton.enabled = True
       
    def addContourFilterWidget(self):      
        contourFilter = ContourFilterWidget(parent=self.keywordsScrollWidget)       
        self.keywordsScrollWidget.layout().addRow(contourFilter)
    
    def getContourFilters(self):      
        contourFilterWidgets = [childWidget for childWidget in self.keywordsScrollWidget.children() if childWidget.className()=="ContourFilterWidget"]
        if len(contourFilterWidgets) == 0: return None

        contourFilters = [filterWidget.getContourFilterDict() for filterWidget in contourFilterWidgets]
        return contourFilters
        
    def onBatchApply(self):
        self.applyBatchButton.enabled = False
        
        if self.nrrdButton.checked: self.fileFormat = ".nrrd"
        elif self.niftiButton.checked: self.fileFormat = ".nii"
        
        if self.metadataButton.checked: self.inferPatientID = "metadata"
        elif self.inputDirButton.checked: self.inferPatientID = "inputdir"
        
        self.contourFilters = self.getContourFilters()
        #batchConverterTools.BatchConvertDICOMtoNRRD.batchConvert(self.inputPatientDir, self.outputPatientDir, self.contourFilters, self.inferPatientID, self.fileFormat)
        
        if self.extractCSVButton.checked:
            DicomHeaderParserInstance = batchConverterTools.MetadataExtractor.DicomHeaderParser(self.inputPatientDir)
            DicomHeaderParserInstance.ExecuteDicomHeaderParser()
            DicomHeaderParserInstance.WriteToCSVFile(outputDir=self.outputPatientDir)        
            
        self.applyBatchButton.enabled = True
        self.applyBatchButton.text = "Apply Batch Convert"

    
        
    def onReload(self, moduleName="batchConverter"):
        #Generic reload method for any scripted module.
        #ModuleWizard will subsitute correct default moduleName.
    
        import imp, sys, os, slicer
    
        widgetName = moduleName + "Widget"
     
        # reload the source code
        # - set source file path
        # - load the module to the global space
        filePath = eval('slicer.modules.%s.path' % moduleName.lower())
        p = os.path.dirname(filePath)
        if not sys.path.__contains__(p):
          sys.path.insert(0,p)
        fp = open(filePath, "r")
        globals()[moduleName] = imp.load_module(
            moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
        fp.close()
     
        # rebuild the widget
        # - find and hide the existing widget
        # - create a new widget in the existing parent
        # parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent()
        parent = self.parent
        for child in parent.children():
          try:
            child.hide()
          except AttributeError:
            pass
        globals()[widgetName.lower()] = eval(
            'globals()["%s"].%s(parent)' % (moduleName, widgetName))
        globals()[widgetName.lower()].setup()

    
class ContourFilterWidget(qt.QWidget):
    def __init__(self, parent=None):
        super(ContourFilterWidget, self).__init__(parent)
        
        self.contourName = qt.QLineEdit("")
        self.contourName.setPlaceholderText("Output Label Name")
        self.inputKeywords = qt.QLineEdit("")
        self.inputKeywords.setPlaceholderText("Search Keywords")
        self.excludeKeywords = qt.QLineEdit("")
        self.excludeKeywords.setPlaceholderText("Exclusion Keywords")
        self.deleteButton = qt.QPushButton("Delete")
        self.deleteButton.connect('clicked()', self.delete) 
        
        layout = qt.QHBoxLayout()
        layout.addWidget(self.contourName)
        layout.addWidget(self.inputKeywords)
        layout.addWidget(self.excludeKeywords)
        layout.addWidget(self.deleteButton)
        self.setLayout(layout)
        
    def getContourFilterDict(self):  
        if self.inputKeywords.text == '': inputContourKeywords = []   
        else: inputContourKeywords = [str(keyword.strip()) for keyword in self.inputKeywords.text.split(',')]
        
        if self.excludeKeywords.text == '': excludeContourKeywords = []       
        else: excludeContourKeywords = [str(keyword.strip()) for keyword in self.excludeKeywords.text.split(',')]        
        
        contourFilter = {"Name": str(self.contourName.text.strip()), "Include": inputContourKeywords, "Exclude": excludeContourKeywords}
        
        return contourFilter
        

        
        
            