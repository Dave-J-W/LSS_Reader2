#!/usr/bin/env python
import sys
import os
import numpy as np
from lss_core.numbers import spec_number, spec_numbers

class mcaread:
    def __init__(self, mcafile, beamline='APS-15IDC'):
        self.Data={}
        self.Par={}
        self.mcafile=mcafile
        if beamline=='APS-15IDC':
            self.APS_15IDC()
        if beamline!='APS-15IDC':
            raise ValueError('unsupported beamline %r: only APS-15IDC files can be read' % (beamline,))
    
    
    def APS_15IDC(self):
        """
        Function to read a complete spec mca collected at APS 15IDC 
        """
        fid=open(self.mcafile)
        fdata=fid.readlines()
        fid.close()
        if fdata[0][:2]!='#F':
            self.Data['NumOfScans']=0
            self.Data['Message']='The file is not a valid specfile!!'
            print ('Error:: The file is not a valid specfile!!')
        else:
            startScanLineNums=[i for i in range(len(fdata)) if fdata[i][:2]=='#S']
            self.Data['StartScanLineNums']=startScanLineNums
            numOfScans=len(self.Data['StartScanLineNums'])
            self.Data['NumOfScans']=numOfScans
            scanLines=[fdata[i] for i in startScanLineNums]
            self.Data['ScanLines']=scanLines
            for i in range(numOfScans):
                start=startScanLineNums[i]+1
                line=fdata[start]
                self.Data[i]={}
                self.Par[i]={}
                tmpdata=[]
                for w in scanLines[i].split():
                    if w.startswith('Point:'):       # per-point files (mca_save_point)
                        try:
                            self.Par[i]['Point']=int(w[6:])
                        except ValueError:
                            pass
                while line[:2]!='@A':
                    if line[:10]=='#@CHANNEL ':      # detector element of a multi-element file
                        try:
                            self.Par[i]['Channel']=int(line[10:].split()[0])
                        except (ValueError,IndexError):
                            pass
                    if line[:7]=='#@CTIME':
                        tmppar=line[7:].split()
                        self.Par[i]['Time']=spec_numbers(tmppar)
                    if line[:5]=='#Monc':
                        tmppar=line[5:].split()
                        self.Data[i]['Monc']=spec_number(tmppar[0])
                        try: # When running for Hutch B and D
                            self.Data[i]['Monb']=spec_number(tmppar[1])
                            self.Data[i]['Mond']=spec_number(tmppar[2])
                        except:
                            pass
                    if line[:2]=='#Q':
                        tmppar=line[2:].split()
                        self.Par[i]['Q']=spec_numbers(tmppar)
                    if line[:7]=='#@CALIB':
                        tmppar=line[7:].split()
                        self.Par[i]['Calib']=spec_numbers(tmppar)
                    if line[:7]=='#Energy':
                        tempar=line[7:].split()
                        self.Par[i]['Energy']=spec_number(tempar[0])
                    start=start+1
                    line=fdata[start]
                self.Data[i]['Vortex']=spec_numbers(line[2:-2].split())
                start=start+1
                line=fdata[start]
                while line!='\n':
                    if line[-2]=='\\':
                        self.Data[i]['Vortex'].extend(spec_numbers(line[:-2].split()))
                    else:
                        self.Data[i]['Vortex'].extend(spec_numbers(line[:-1].split()))
                    start=start+1
                    line=fdata[start]
                if len(self.Par[i])==0:
                    self.Par[i]['Message']='No parameters!!'
