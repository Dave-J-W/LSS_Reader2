#!/usr/bin/env python
import sys
import os
import re
import numpy as np
from lss_core import paths
from lss_core.numbers import spec_number, spec_numbers
from lss_core.monitor import parse_gain
from lss_core.series import parse_series, aborted_after

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


def complete_rows(rows):
    """The data rows of a scan that have its usual number of values, and
    [(row index, number of values)] of the others: a line SPEC is still
    writing (a live file) or a damaged one. One short row made every column
    of its scan None, because numpy cannot stack rows of unequal length
    (the fragility audit, 2026-11-23). The usual number is the commonest,
    the larger on a tie (a partial line is shorter)."""
    if not rows:
        return rows, []
    counts = {}
    for r in rows:
        counts[len(r)] = counts.get(len(r), 0) + 1
    usual = max(counts, key=lambda w: (counts[w], w))
    return [r for r in rows if len(r) == usual], [(k, len(r)) for k, r in enumerate(rows) if len(r) != usual]


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
            # file headers (#E Unix s, #D local) above each scan: the time zone of
            # its #D (lss_core.timing); a file can hold several, one per SPEC session
            fileheads=[]
            for k_e,l_e in enumerate(fdata):
                if l_e[:2]=='#E':
                    d_e=next((x for x in fdata[k_e+1:k_e+4] if x[:2]=='#D'),'')
                    try:
                        fileheads.append((k_e,float(l_e[2:].split()[0]),d_e[2:].strip()))
                    except (ValueError,IndexError):
                        pass
            # the file header's full motor names (#O0, #O1, ...), position for position
            # with the scans' #P names, which the macro cuts to 8 characters
            # ('Two_Thet' for 'Two_Theta'; TODO area L, 2026-11-24)
            motorheads=[]
            for k_e,l_e in enumerate(fdata):
                if l_e[:2]=='#O' and l_e[2:3].isdigit():
                    tag=l_e.split()[0]
                    if tag=='#O0' or not motorheads:
                        motorheads.append((k_e,{}))
                    motorheads[-1][1][int(tag[2:])]=re.split(r'\s{2,}',l_e[len(tag):].strip())
            if motorheads:
                self.Data['MotorNames']=motorheads[-1][1]
            self.lastAbsorber=self.Data.get('LastAbsorber') if startLineNum>0 else None
            self.lastMoncGain=self.Data.get('LastMoncGain') if startLineNum>0 else None
            for i in range(numOfScans): 
                start=startScanLineNums[i]+1
                onames=next((h[1] for h in reversed(motorheads) if h[0]<startScanLineNums[i]),
                            self.Data.get('MotorNames') or {})
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
                absorber_a=None     # (value,) from #A: it wins over the Absorber motor of #P, whatever the order
                while line[:2]!='\n' and line[:2]!='#C':
                    if line[:2]=='#P':
                        parName=line[4:].split()
                        start=start+1
                        parValue=spec_numbers(fdata[start][1:].split())
                        for j in range(len(parName)):
                            self.Par[num][parName[j]]=parValue[j]
                        try:
                            full=onames.get(int(line.split()[0][2:]),[])
                        except ValueError:
                            full=[]
                        if len(full)==len(parName):   # the full name too, where the macro cut it
                            for j,(short,name) in enumerate(zip(parName,full)):
                                if name!=short and name.startswith(short) and name not in self.Par[num]:
                                    self.Par[num][name]=parValue[j]
                        for j,name in enumerate(parName):   # and the 8-character name, where a macro writes it whole
                            if len(name)>8 and name[:8] not in self.Par[num]:
                                self.Par[num][name[:8]]=parValue[j]
                    if line[:2]=='#W':
                        tmppar=line[2:].split()
                        self.Par[num]['Wavelength']=spec_number(tmppar[1])
                    if line[:3]=='#G0':
                        self.Par[num]['g_l1']=float(line[4:].split()[5])
                        self.Par[num]['g_l2']=float(line[4:].split()[6])
                        self.Par[num]['g_l3']=float(line[4:].split()[7])
                    if line[:2]=='#M' and line[2:].split()[:2]==['Monc','Gain']:
                        # SR570 sensitivity (lss_core.monitor); None: unknown
                        self.Par[num]['MoncGainText']=' '.join(line[2:].split()[2:])
                        self.Par[num]['MoncGain']=parse_gain(line[2:].split()[2:])
                    if line[:2]=='#A':
                        # an unreadable value ("#A Absorber " with nothing after it,
                        # seen in a real file) is unknown, not a setting: None, with
                        # the text kept (it was 63, which is a real setting, D38)
                        tmppar=line[2:].split()
                        self.Par[num]['AbsorberText']=' '.join(tmppar[1:])
                        try:
                            self.Par[num]['Absorber']=spec_number(tmppar[1])
                        except (IndexError,ValueError,TypeError,SyntaxError):
                            self.Par[num]['Absorber']=None
                        absorber_a=(self.Par[num]['Absorber'],)
                    if line[:2]=='#Q':
                        tmppar=line[2:].split()
                        self.Par[num]['Q']=spec_numbers(tmppar)

                    if line[:2]=='#V':
                        self.Par[num]['Detector']='Vortex'
                    if line[:3]=='#B0':
                        # the image name's extension and last field, by splitext: a SPEC
                        # name with a dot (run.v2) hid the scan's images (TODO area L)
                        image=line[3:].strip()
                        self.Par[num]['ImageNumber']=len(paths.stem(image).split('_')[-1])
                        if paths.ext(image)=='.tif':
                            self.Par[num]['Detector']='Pilatus'
                        elif paths.ext(image)=='.sfrm':
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
                # the rest of this scan's block: SPEC's abort comment and a
                # series end line follow the data (lss_core.series)
                k=i-tmp
                stop=startScanLineNums[k+1] if k+1<len(startScanLineNums) else len(fdata)
                extras={}       # merged after the 'No parameters' check below, which counts header values only
                head=[h for h in fileheads if h[0]<startScanLineNums[k]]
                if head:
                    extras['FileEpoch'],extras['FileDate']=head[-1][1],head[-1][2]
                for extra in fdata[startScanLineNums[k]+1:stop]:
                    if extra[:2]=='#D' and 'Date' not in extras:
                        extras['Date']=extra[2:].strip()      # the scan's own date (local, no zone)
                    if extra[:2]=='#U':
                        words=extra[2:].split()
                        if words[:1]==['SeriesT0']:
                            try:
                                extras['SeriesT0']=float(words[1])   # macro start, Unix s (new files)
                            except (IndexError,ValueError):
                                pass
                        if words[:1]==['Series']:
                            # scan series (F39): '#U Series id=.. i=.. n=.. kind=..'
                            extras['Series']=parse_series(words[1:])
                        elif words[:1]==['SeriesMacro']:
                            extras['SeriesMacro']=' '.join(words[1:])
                    if extra[:2]=='#C':
                        n_ab=aborted_after(extra)
                        if n_ab is not None:
                            extras['AbortedAfter']=n_ab
                        words=extra[2:].split()
                        if 'Series' in words and 'end' in words:
                            extras['SeriesEnd']=parse_series(words[words.index('Series')+1:])
                if self.Data[num]['ScanVar']!='Empty':
                    tmpdata,dropped=complete_rows(tmpdata)
                    if dropped:
                        extras['DroppedRows']=dropped
                    if tmpdata and len(tmpdata[0])!=len(scanVar):
                        # #L names more or fewer columns than the rows hold (a label with a space,
                        # "Two Theta", in a macro that does not join them): the columns are
                        # still matched by position, as they always were, but now it is said
                        # (TODO area L, 2026-11-24): (labels, values per row)
                        extras['LabelMismatch']=(len(scanVar),len(tmpdata[0]))
                    for j in range(len(scanVar)):
                        try:
                            self.Data[num][scanVar[j]]=np.array(tmpdata,dtype='float')[:,j]
                        except:
                            self.Data[num][scanVar[j]]=None
                if absorber_a is not None:
                    # #A is the absorber setting; the motor of #P4 named Absorber gives the
                    # same in NX files, where #A comes after #P and so won by order. Now it
                    # wins by rule (TODO area L, 2026-11-24); the motor's value is kept
                    if self.Par[num].get('Absorber',absorber_a[0])!=absorber_a[0]:
                        self.Par[num]['AbsorberMotor']=self.Par[num]['Absorber']
                    self.Par[num]['Absorber']=absorber_a[0]
                if len(self.Par[num])==1:
                    self.Par[num]['Message']='No parameters!!'
                self.Par[num].update(extras)
                if 'Absorber' in self.Par[num]:
                    self.lastAbsorber=(self.Par[num]['Absorber'],num)
                elif self.lastAbsorber is not None:
                    # no #A in this scan (getandsave_mca writes none): the
                    # absorbers do not change during a scan, so the setting is
                    # the last #A above it in the file (owner, 2026-11-17, F50)
                    self.Par[num]['Absorber']=self.lastAbsorber[0]
                    self.Par[num]['AbsorberFrom']=self.lastAbsorber[1]
                if 'MoncGainText' in self.Par[num]:
                    self.lastMoncGain=(self.Par[num]['MoncGain'],self.Par[num]['MoncGainText'],num)
                elif self.lastMoncGain is not None:
                    # no #M in this scan (getandsave_mca): the last one above it
                    self.Par[num]['MoncGain'],self.Par[num]['MoncGainText'],self.Par[num]['MoncGainFrom']=self.lastMoncGain
                self.progressDialog.setLabelText('Reading Scan #'+str(num))         
                self.updateProgress()
                self.Data['NumOfScans']=num
#                self.Data['ScanLines']=self.Data['ScanLines']+[scanLines[num-tmp]]
                self.Data[num]['ScanLine']=fdata[startScanLineNums[i-tmp]]
                self.Data[num]['StartScanLineNum']=startScanLineNums[i-tmp]
                self.endLineNum=startScanLineNums[i-tmp]
                # an update re-reads the last scan (it may have grown): its number is
                # listed already (2026-11-22: it was listed twice, so every "Update
                # Specfile" warned of a repeated scan and split the series guess)
                if not (startLineNum>0 and i==tmp and self.Data['ScanNums'] and self.Data['ScanNums'][-1]==num):
                    self.Data['ScanNums'].append(num)
                self.Data['LastAbsorber']=self.lastAbsorber
                self.Data['LastMoncGain']=self.lastMoncGain
                if self.progressDialog.wasCanceled()==True:
                    break
        self.progressDialog.hide()
