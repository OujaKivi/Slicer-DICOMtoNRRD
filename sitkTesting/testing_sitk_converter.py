# -*- coding: utf-8 -*-
"""
Created on Fri Nov 06 14:38:31 2015

@author: Vivek Narayan
"""

import SimpleITK as sitk
import collections
import dicom
import os
import fnmatch
import csv
import glob

# order dicom files in seriesinstanceuid by sopinstanceuid.split('.')[-1]

def setHeaderTagsToNamesDict():
    headerTagsNames_dict = collections.OrderedDict()
    for name,tag in dicom.datadict.keyword_dict.iteritems():
        headerTagsNames_dict[tag] = name
    headerTagsNames_dict = collections.OrderedDict(sorted(headerTagsNames_dict.items(), key=lambda t: t[0]))
    return headerTagsNames_dict

headerTagsNames_dict = setHeaderTagsToNamesDict()
    
dirin = ""
dirout = ""

logfp = os.path.join(dirout, 'logfile.txt')

dcmReader = sitk.ImageSeriesReader()
nrrdWriter = sitk.ImageFileWriter()

patientDirs = glob.glob(os.path.join(dirin,'*'))
for ind, patientDir in enumerate(patientDirs):
    dicomFiles_list = []
    for r,d,f in os.walk(patientDir):
        if True#'CT' in r:
          [dicomFiles_list.append(str(os.path.join(r,fle))) for fle in f if '._' not in fle] #fnmatch.filter(f,'*.dcm')]
        
    dicomSeriesFileList_Dict = {}
    for dicomFile in dicomFiles_list:
        dicomFileHeader = dicom.read_file(dicomFile, force=True)
        try:
          seriesInstanceUID = str(dicomFileHeader[2097166].value)
        except KeyError:
          continue
        
        dicomFileDict = {tag:str(element.value) for (tag,element) in dicomFileHeader.iteritems() if '\x00' not in str(element.value)}
        dicomFileDict = collections.OrderedDict(sorted(dicomFileDict.items(), key=lambda t: t[0]))
        dicomFileDict['Filepath'] = str(dicomFile)   
        if dicomFileDict[524384] == 'RTSTRUCT': continue
        else:  
            if seriesInstanceUID in reversed(dicomSeriesFileList_Dict.keys()):
                dicomSeriesFileList_Dict[seriesInstanceUID].append(dicomFileDict)
            else: 
                dicomSeriesFileList_Dict[seriesInstanceUID] = []
                dicomSeriesFileList_Dict[seriesInstanceUID].append(dicomFileDict)

    for series in dicomSeriesFileList_Dict:
        with open(logfp, 'a') as logfile:
            logfile.write('Converting Series: ' + series + ' from Patient: ' + os.path.basename(patientDir))
        patientID = os.path.basename(patientDir)
        outputPatientDir = os.path.join(dirout, patientID)
        if not os.path.exists(outputPatientDir): os.mkdir(outputPatientDir)
        
        try:
            studyDate = dicomSeriesFileList_Dict[series][0][524320]
        except KeyError:
            studyDate = 'UnknownStudy'
        finally:
            studyDate = ''.join(x for x in studyDate if x not in "-',;\/:*?<>|").strip()
            if studyDate == '': studyDate = 'UnknownStudy'             
            outputStudyDir = os.path.join(outputPatientDir, studyDate)
            if not os.path.exists(outputStudyDir): os.mkdir(outputStudyDir)
          
        outputReconstructionsDir = os.path.join(outputStudyDir, 'Reconstructions')
        outputSegmentationsDir = os.path.join(outputStudyDir, 'Segmentations')
        outputResourcesDir = os.path.join(outputStudyDir, 'Resources')
        if not os.path.exists(outputReconstructionsDir): os.mkdir(outputReconstructionsDir)
        if not os.path.exists(outputSegmentationsDir): os.mkdir(outputSegmentationsDir) 
        if not os.path.exists(outputResourcesDir): os.mkdir(outputResourcesDir)
          
        try: 
            seriesDescription = dicomSeriesFileList_Dict[series][0][528432]
        except KeyError:
            seriesDescription = patientID + '_' + studyDate + '_' + 'CT'
        finally:  
            seriesDescription = ''.join(x for x in seriesDescription if x not in "-',;\/:*?<>|").strip()
            outputFilename = str(seriesDescription + '.nrrd')
        
        fps = []
        dirp = os.path.dirname(dicomSeriesFileList_Dict[series][0]['Filepath'])
        fps = glob.glob(os.path.join(dirp,'*'))
        dcmReader.SetFileNames(fps)
        dcmImage = dcmReader.Execute()
        with open(logfp, 'a') as logfile:
            [logfile.write('\t' + fp +'\n') for fp in fps]
        #if file naming schema is like CT.rtp1.1.surv_43062.1.T.-7.4.CT.dcm --- take last two numbers as slice positions (i.e. -7.4mm) and re arrange filepaths list accordingly    
        outpath = os.path.join(outputReconstructionsDir, outputFilename)
        nrrdWriter.SetFileName(outpath)
        nrrdWriter.Execute(dcmImage)
        print 'Converted:', patientID, '------', ind+1, 'out of', len(patientDirs)

"""            
dicomFiles_list = []
for r,d,f in os.walk(dirin):
    if 'CT' in r:
      [dicomFiles_list.append(str(os.path.join(r,fle))) for fle in f if '._' not in fle] #fnmatch.filter(f,'*.dcm')]
    
dicomSeriesFileList_Dict = {}
for dicomFile in dicomFiles_list:
    dicomFileHeader = dicom.read_file(dicomFile, force=True)
    try:
      seriesInstanceUID = str(dicomFileHeader[2097166].value)
    except KeyError:
      continue
    
    dicomFileDict = {tag:str(element.value) for (tag,element) in dicomFileHeader.iteritems() if '\x00' not in str(element.value)}
    dicomFileDict = collections.OrderedDict(sorted(dicomFileDict.items(), key=lambda t: t[0]))
    dicomFileDict['Filepath'] = str(dicomFile)   
    if dicomFileDict[524384] == 'RTSTRUCT': continue
    else:  
        if seriesInstanceUID in reversed(dicomSeriesFileList_Dict.keys()):
            dicomSeriesFileList_Dict[seriesInstanceUID].append(dicomFileDict)
        else: 
            dicomSeriesFileList_Dict[seriesInstanceUID] = []
            dicomSeriesFileList_Dict[seriesInstanceUID].append(dicomFileDict)

dcmReader = sitk.ImageSeriesReader()
nrrdWriter = sitk.ImageFileWriter()

for ind, series in enumerate(dicomSeriesFileList_Dict):   
    patientID = os.path.basename(os.path.dirname(os.path.dirname(dicomSeriesFileList_Dict[series][0]['Filepath']))) #dicomSeriesFileList_Dict[series][0][1048608] #
    patientID = ''.join(x for x in patientID if x not in "-',;\/:*?<>|").strip()
    outputPatientDir = os.path.join(dirout, patientID)
    if not os.path.exists(outputPatientDir): os.mkdir(outputPatientDir)
    
    studyDate = dicomSeriesFileList_Dict[series][0][524320]
    studyDate = ''.join(x for x in studyDate if x not in "-',;\/:*?<>|").strip()
    outputStudyDir = os.path.join(outputPatientDir, studyDate)
    if not os.path.exists(outputStudyDir): os.mkdir(outputStudyDir)
      
    outputReconstructionsDir = os.path.join(outputStudyDir, 'Reconstructions')
    outputSegmentationsDir = os.path.join(outputStudyDir, 'Segmentations')
    outputResourcesDir = os.path.join(outputStudyDir, 'Resources')
    if not os.path.exists(outputReconstructionsDir): os.mkdir(outputReconstructionsDir)
    if not os.path.exists(outputSegmentationsDir): os.mkdir(outputSegmentationsDir) 
    if not os.path.exists(outputResourcesDir): os.mkdir(outputResourcesDir)
      
    try: 
        seriesDescription = dicomSeriesFileList_Dict[series][0][528432]
    except KeyError:
        seriesDescription = patientID + '_' + studyDate + '_' + '_CT'
    finally:  
        seriesDescription = ''.join(x for x in seriesDescription if x not in "-',;\/:*?<>|").strip()
        outputFilename = str(seriesDescription + '.nrrd')

    sopinstanceuid_map = {}
    fps = []
    dirp = os.path.dirname(dicomSeriesFileList_Dict[series][0]['Filepath'])
    fps = glob.glob(os.path.join(dirp,'*')) #if no rtstruct files
         
    #for dicomFileDict in dicomSeriesFileList_Dict[series]:
    #    sop = os.path.splitext(os.path.basename(dicomFileDict['Filepath']))[0].split('_')[-1] #dicomFileDict[524312].split('.')[-1]
    #    sop = int(sop)        
    #    sopinstanceuid_map[sop] = dicomFileDict['Filepath']
    ##seq = dcmReader.GetGDCMSeriesFileNames(dirin, series, recursive=True, loadSequences=True)
    #sopinstanceuid_map = collections.OrderedDict(sorted(sopinstanceuid_map.items(), key=lambda t: t[0]))        
    #dcmReader.SetFileNames(sopinstanceuid_map.values()) #dcmReader.SetFileNames(seq) 
    
    dcmReader.SetFileNames(fps)
    dcmImage = dcmReader.Execute()
        
    outpath = os.path.join(outputReconstructionsDir, outputFilename)
    nrrdWriter.SetFileName(outpath)
    nrrdWriter.Execute(dcmImage)
    print 'Converted:', patientID, '------', ind+1, 'out of', len(dicomSeriesFileList_Dict.keys())
"""    
"""          
dicomHeaderInformationTable = []    
for headerTag,headerName in headerTagsNames_dict.iteritems():
    headerTagFileValuesRow = []
    for series in dicomSeriesFileList_Dict:
        for dicomFileDict in dicomSeriesFileList_Dict[series]:  
            try:
                dicomFileTagValue = str(dicomFileDict[headerTag])
            except KeyError:
                dicomFileTagValue = ''
            finally:
                if not dicomFileTagValue: dicomFileTagValue = ''
                headerTagFileValuesRow.append(dicomFileTagValue.replace(',',''))
        if any(headerTagFileValuesRow): dicomHeaderInformationTable.append([headerName] + headerTagFileValuesRow) 
dicomHeaderInformationTable = zip(*dicomHeaderInformationTable)


outputCSVFile = os.path.join(dirin, 'dicom_metadata.csv')
with open(outputCSVFile, 'wb') as csvf:
    writer = csv.writer(csvf)
    for row in dicomHeaderInformationTable:
        writer.writerow(row)         
"""