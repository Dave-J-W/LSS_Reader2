#!/usr/bin/env python
import sys
import os
import numpy as np
from lss_core.numbers import spec_number, spec_numbers

def is_spec_file(path):
    """True if ``path`` can be read and starts like a SPEC data file (#F)."""
    try:
        with open(path, 'rb') as fid:
            return fid.read(2) == b'#F'
    except OSError:
        return False


class _NoProgress:
    """Stands in for a progress dialog when reading from a script."""
    def __init__(self):
        self._value = 0
    def value(self):
        return self._value
    def setValue(self, v):
        self._value = v
    def wasCanceled(self):
        return False
    def __getattr__(self, name):          # setMaximum, setLabelText, show, hide, ...
        return lambda *a, **k: None


class specread:
    def __init__(self, specfile, startLineNum=0, endScanNum=0, beamline='APS-15IDC',det='CCD',data=None,par=None,progress=None):
        # progress: an object with the QProgressDialog methods used below (the
        # window passes one); None reads silently, so no Qt is needed
        self.progressDialog=progress if progress is not None else _NoProgress()
        # fresh dictionaries per reader unless the caller passes its own (refresh)
        self.Data={} if data is None else data
        self.Par={} if par is None else par
        self.specfile=specfile
        if beamline=='APS-15IDC':
            self.APS_15IDC(startLineNum=startLineNum, endScanNum=endScanNum, det=det)
        if beamline!='APS-15IDC':
            raise ValueError('unsupported beamline %r: only APS-15IDC files can be read' % (beamline,))
        
    def updateProgress(self):
        self.progressDialog.setValue(self.progressDialog.value()+1)

    
    
    def APS_15IDC(self,startLineNum=0, endScanNum=0, det='CCD'):
        """
        Function to read a complete spec File collected at APS 15IDC 
        """
        self.Data['YCol']='Apex2'
        self.Data['NCol']='Monc'
        fid=open(self.specfile)
        fdata=fid.readlines()
        self.SpecFileFull=fdata
        fid.close()
        if len(fdata)==0 or fdata[0][:2]!='#F':
            self.endLineNum=0
            self.Data['NumOfScans']=0
            self.Data['Message']='The file is not a valid specfile!!'
            print ('Error:: The file is not a valid specfile!!')
        else:
            startScanLineNums=[i for i in range(startLineNum,len(fdata)) if fdata[i][:2]=='#S']
            self.progressDialog.setMaximum(len(startScanLineNums))
            self.progressDialog.show()
            if startLineNum>0:
                startScanLineNums=sorted(startScanLineNums)
            numOfScans=len(startScanLineNums)
            scanLines=[fdata[i] for i in startScanLineNums]
            if startLineNum==0:
                tmp=0
                self.Data['NumOfScans']=0#numOfScans
                self.Data['ScanNums']=[]
                offset=0
#                self.Data['ScanLines']=[]#scanLines
#                self.Data['StartScanLineNums']=[]#startScanLineNums
            else:
                tmp=self.Data['NumOfScans']
                self.Data['NumOfScans']=self.Data['NumOfScans']-1#+numOfScans
                offset=1
#                self.Data['ScanLines']=self.Data['ScanLines'][:-1]#+scanLines[1:]
#                self.Data['StartScanLineNums']=self.Data['StartScanLineNums'][:-1]#+startScanLineNums
            if int(scanLines[-1].split()[1])!=len(startScanLineNums)+endScanNum-offset:
                print (len(startScanLineNums), scanLines[-1].split()[1], endScanNum)
                self.Data['Error']=True
                self.Data['Message']='There are identical scans in the file'
            else:
                self.Data['Error']=False
            # (value, scan) of the last #A read; kept in Data between
            # incremental reads so that a refresh continues from it
            self.lastAbsorber=self.Data.get('LastAbsorber') if startLineNum>0 else None
            for i in range(numOfScans): 
                start=startScanLineNums[i]+1
                line=fdata[start]
                num=int(fdata[startScanLineNums[i]].split()[1])
                i=i+tmp
                self.Data[num]={}
                self.Par[num]={}
                if fdata[start-1].split()[2]=='getandsave_mca':
                    self.Par[num]['Detector']='Vortex'
                    self.Data[num]['ScanVar']='Empty'
                else:
                    self.Par[num]['Detector']='Monitor'
                tmpdata=[]
                while line[:2]!='\n' and line[:2]!='#C':
                    if line[:2]=='#P':
                        parName=line[4:].split()
                        start=start+1
                        parValue=spec_numbers(fdata[start][1:].split())
                        for j in range(len(parName)):
                            self.Par[num][parName[j]]=parValue[j]
                    if line[:2]=='#W':
                        tmppar=line[2:].split()
                        self.Par[num]['Wavelength']=spec_number(tmppar[1])
                    if line[:3]=='#G0':
                        self.Par[num]['g_l1']=float(line[4:].split()[5])
                        self.Par[num]['g_l2']=float(line[4:].split()[6])
                        self.Par[num]['g_l3']=float(line[4:].split()[7])
                    if line[:2]=='#A':
                        try:
                            tmppar=line[2:].split()
                            self.Par[num]['Absorber']=spec_number(tmppar[1])
                        except:
                            self.Par[num]['Absorber'] = 63
                    if line[:2]=='#Q':
                        tmppar=line[2:].split()
                        self.Par[num]['Q']=spec_numbers(tmppar)
                    if line[:2]=='#V':
                        self.Par[num]['Detector']='Vortex'
                    if line[:3]=='#B0':
                        tmppar=line[3:].split('.')
                        self.Par[num]['ImageNumber']=len(line[3:].split('_')[-1].split('.')[0])
                        if tmppar[1]=='tif\n':
                            self.Par[num]['Detector']='Pilatus'
                        elif tmppar[1]=='sfrm\n':
                            self.Par[num]['Detector']='Unsupported'   # Bruker CCD (.sfrm) images: no longer supported
                    if line[:3]=='#B1':
                        try:
                            tmppar=spec_numbers(line[3:].split())
                        except:
                            tmppar=spec_numbers(line[3:].split()[:-1])
                        self.Par[num]['DBPos']=tmppar[:2]
                        self.Par[num]['S2D_Dist']=tmppar[2]
                        self.Par[num]['S7D_Dist']=tmppar[3]
                    if line[:3]=='#B2':
                        tmppar=spec_numbers(line[3:].split())
                        self.Par[num]['DBPos']=tmppar[:2]
                        self.Par[num]['S2D_Dist']=tmppar[2]
                        self.Par[num]['S7D_Dist']=tmppar[3]
                    if line[:2]=='#L':
                        scanVar=line[3:-1].split()
                        self.Data[num]['ScanVar']=scanVar
                    if line[0]!='#':
                        try:
                            tmpdata.append(spec_numbers(line.split(  )))
                        except:
                            self.Data[num]['Message']='Something wrong with Scan Number %d',num,'.Please check the the scan in the specfile.'
                            print ('Something wrong with Scan Number %d',num)
                    start=start+1
                    try:
                        line=fdata[start]
                    except:
                        break
                if self.Data[num]['ScanVar']!='Empty':
                    for j in range(len(scanVar)):
                        try:
                            self.Data[num][scanVar[j]]=np.array(tmpdata,dtype='float')[:,j]
                        except:
                            self.Data[num][scanVar[j]]=None
                if len(self.Par[num])==1:
                    self.Par[num]['Message']='No parameters!!'
                if 'Absorber' in self.Par[num]:
                    self.lastAbsorber=(self.Par[num]['Absorber'],num)
                elif self.lastAbsorber is not None:
                    # no #A in this scan (getandsave_mca writes none): the
                    # absorbers do not change during a scan, so the setting is
                    # the last #A above it in the file (owner, 2026-11-17, F50)
                    self.Par[num]['Absorber']=self.lastAbsorber[0]
                    self.Par[num]['AbsorberFrom']=self.lastAbsorber[1]
                self.progressDialog.setLabelText('Reading Scan #'+str(num))         
                self.updateProgress()
                self.Data['NumOfScans']=num
#                self.Data['ScanLines']=self.Data['ScanLines']+[scanLines[num-tmp]]
                self.Data[num]['ScanLine']=fdata[startScanLineNums[i-tmp]]
                self.Data[num]['StartScanLineNum']=startScanLineNums[i-tmp]
                self.endLineNum=startScanLineNums[i-tmp]
                self.Data['ScanNums'].append(num)
                self.Data['LastAbsorber']=self.lastAbsorber
                if self.progressDialog.wasCanceled()==True:
                    break
        self.progressDialog.hide()
