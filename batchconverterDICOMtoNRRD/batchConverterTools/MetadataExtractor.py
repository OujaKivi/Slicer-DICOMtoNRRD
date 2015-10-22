import os
import fnmatch
import dicom
import csv
import collections

class DicomHeaderParser:
  
    def __init__(self, dicomDir, initHeaderTag_list=None):
        self.dicomDir = dicomDir
        if initHeaderTag_list is not None:
            self.initHeaderTag_list = initHeaderTag_list
        else:
            # Note: The 7-digit integers in self.initHeaderTag_list are converted from the 
            # hex string value of DICOM tags of interest in order to be compatible with dicom.datadict.keyword_dict 
            self.initHeaderTag_list = [1048592,1048608,524320,528446,524321,528432,524384]
            #1048592: Patient Name
            #1048608: Patient ID
            #524320: Study Date
            #528446: Study Description
            #524321: Series Date
            #528432: Series Description
            #524384: Modality
        
        self.dicomHeaderInformationTable = []
        self.headerTagsNames_dict = {}
        self.dicomFiles_list = []
        self.dicomFileDict_list = []
        self.dicomSeriesInstanceUIDs_fileCounter = {}
        
        self.headerTagsNames_dict = self.setHeaderTagsToNamesDict()
      
    
    def setHeaderTagsToNamesDict(self):
        headerTagsNames_dict = collections.OrderedDict()
        for name,tag in dicom.datadict.keyword_dict.iteritems():
            headerTagsNames_dict[tag] = name
        headerTagsNames_dict = collections.OrderedDict(sorted(headerTagsNames_dict.items(), key=lambda t: t[0]))
        return headerTagsNames_dict
  
      
    def getDicomFilesList(self, dicomDir):
        dicomFiles_list = []
        for root, directory, filenames in os.walk(dicomDir):
            [dicomFiles_list.append(str(os.path.join(root, file))) for file in fnmatch.filter(filenames, '*.dcm')]  
        return dicomFiles_list
    
        
    def ExecuteDicomHeaderParser(self):
        self.dicomFiles_list = self.getDicomFilesList(self.dicomDir)
        self.dicomFileDict_list = self.getDicomFileDictList(self.dicomFiles_list)
        self.dicomHeaderInformationTable = self.populateDicomHeaderInformationTable(self.headerTagsNames_dict, self.dicomFileDict_list, self.initHeaderTag_list)
    
      
    def getDicomFileDictList(self, dicomFiles_list):
        # Returns dictionary with keys of patientIDs and values being dictionaries of header values for every 
        # dicom file in dicomFiles_list with a unique SeriesInstanceUID
        dicomFileDict_list = []
        self.dicomSeriesInstanceUIDs_fileCounter = {}
        for dicomFile in dicomFiles_list:
            dicomFileHeader = dicom.read_file(dicomFile)
            seriesInstanceUID = str(dicomFileHeader[2097166].value)
            if seriesInstanceUID in reversed(self.dicomSeriesInstanceUIDs_fileCounter.keys()):
                self.dicomSeriesInstanceUIDs_fileCounter[seriesInstanceUID] += 1
                continue
            else:
                self.dicomSeriesInstanceUIDs_fileCounter[seriesInstanceUID] = 1
                dicomFileDict = {tag:str(element.value) for (tag,element) in dicomFileHeader.iteritems() if '\x00' not in str(element.value)}
                dicomFileDict = collections.OrderedDict(sorted(dicomFileDict.items(), key=lambda t: t[0]))
                if dicomFileDict[524384] == 'RTSTRUCT': pass        
                else: dicomFileDict_list.append(dicomFileDict)   
        return dicomFileDict_list
    
        
    def populateDicomHeaderInformationTable(self, headerTagsNames_dict, dicomFileDict_list, initHeaderTag_list):
        dicomHeaderInformationTable = []
        
        if self.dicomSeriesInstanceUIDs_fileCounter:
            headerName = str('FileCount')
            initHeaderTagFileValuesRow = []
            for dicomFileDict in dicomFileDict_list:
                seriesInstanceUID = str(dicomFileDict[2097166])
                try:
                    fileCountValue = str(self.dicomSeriesInstanceUIDs_fileCounter[seriesInstanceUID])
                except KeyError:
                    fileCountValue = str('Unknown')
                finally:
                    initHeaderTagFileValuesRow.append(fileCountValue.replace(',',''))
            dicomHeaderInformationTable.append([headerName] + initHeaderTagFileValuesRow) 
          
        #Initialize the initial fields(tags) of dicomHeaderInformationTable based on initHeaderTag_list
        for initHeaderTag in initHeaderTag_list:
            headerName = str(headerTagsNames_dict[initHeaderTag])
            initHeaderTagFileValuesRow = []
            for dicomFileDict in dicomFileDict_list:
                try:
                    dicomFileTagValue = str(dicomFileDict[initHeaderTag])
                except KeyError:
                    dicomFileTagValue = headerName + ' Not Found'
                finally:
                    if not dicomFileTagValue: dicomFileTagValue = headerName + ' Not Found'
                    initHeaderTagFileValuesRow.append(dicomFileTagValue.replace(',',''))       
            if any(initHeaderTagFileValuesRow): dicomHeaderInformationTable.append([headerName] + initHeaderTagFileValuesRow) 
          
        #Populate rest of Dicom Header Information Table
        for headerTag,headerName in headerTagsNames_dict.iteritems():
            if headerTag not in initHeaderTag_list:
                headerTagFileValuesRow = []
                for dicomFileDict in dicomFileDict_list:
                    try:
                        dicomFileTagValue = str(dicomFileDict[headerTag])
                    except KeyError:
                        dicomFileTagValue = ''
                    finally:
                        if not dicomFileTagValue: dicomFileTagValue = ''
                        headerTagFileValuesRow.append(dicomFileTagValue.replace(',',''))
                if any(headerTagFileValuesRow): dicomHeaderInformationTable.append([headerName] + headerTagFileValuesRow)
        
        #Reverse rows and columns
        dicomHeaderInformationTable = zip(*dicomHeaderInformationTable)        
        return dicomHeaderInformationTable
    
      
    def WriteToCSVFile(self, outputDir=None, outputCSVFileNameSuffix='_Dicom_Header_Information.csv'):
        #Write dicomHeaderInformationTable to a CSV file in dicomDir
        if outputDir is None: outputDir = self.dicomDir
     
        outputCSVFileName = os.path.basename(self.dicomDir) + outputCSVFileNameSuffix
        outputCSVFile = os.path.join(outputDir, outputCSVFileName)
        
        with open(outputCSVFile, 'wb') as csvf:
            writer = csv.writer(csvf)
            for row in self.dicomHeaderInformationTable:
                writer.writerow(row)
