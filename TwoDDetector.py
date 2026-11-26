import struct
from PIL import Image
import numpy as np
import os
import array
import pylab
from scipy.optimize import leastsq
import traceback
from lss_core.images import read_pilatus, PIXEL_MM
from lss_core.errors import LEGACY, MonitorTerms
from lss_core.absorbers import attenuation
  

class TwoDDetector:
    def __init__(self,det):
        """Area Detector Image Reader using Python"""
        self.path=None
        #pylab.rc('text', usetex=True)
        if det=='Pilatus':
            self.pix_size=PIXEL_MM
            #self.hroi=[0,194]
            #self.vroi=[0,486]
        else:
            raise ValueError('unsupported detector '+repr(det))
        self.det=det
        # How errors are combined (lss_core.errors): 'legacy' reproduces the
        # old numbers; 'budget' keeps the monitor part per frame and applies
        # it to whole sums. Set by the window or by lss_core.
        self.errors=LEGACY
        self.monitorTerms=MonitorTerms()
        self.roiParts=None

    def _setTerms(self, terms):
        self.monitorTerms=terms if terms is not None else MonitorTerms()

    def imageDir(self, path):
        """Sets the directory for the Apex2 images"""
        os.chdir(path)
        self.path=os.getcwd()

    def openFile(self,fname,bad_pix=0,bad_fac=1):
        if self.det=='Pilatus':
            # Reading Pilatus Image File#
            #-------------------------------------------#
            path=self.path+'/'+fname if self.path!=None else str(fname)
            try:
                # fast, cached, bit-identical to the former PIL getdata() read
                frame=read_pilatus(path)
            except (OSError,ValueError):
                print  ('The File '+str(fname)+' or Path '+str(self.path)+' doesnot Exist!')
                return -1
            self.imageData=np.array(frame)   # a private, writable copy
            self.imageData, self.imbadPix=self.removeBadPix(self.imageData,iteration=bad_pix, factor=bad_fac)
            #self.imageData=np.fliplr(self.imageData)
            self.errorData=np.sqrt(self.imageData)
            self.NROWS,self.NCOLS=self.imageData.shape
            self.hroi=[0, self.NCOLS-1]
            self.vroi=[0, self.NROWS-1]
           # print self.NCOLS, self.NROWS
           # print self.hroi, self.vroi
            
    def removeBadPix(self,data,iteration=1,factor=1):
        """
        Do Bad pixel correction of data with given number of iterations
        
        """
       # mnz=np.min(data[np.nonzero(data)])  #get non-zero min from data
        avg=(np.sqrt(np.average(data))+2)**2
        for i in range(iteration):
            tre=(2+2*iteration)/iteration  #set the threshold value
            databig=np.insert(data,-1,data[:,-1],axis=1)
            databig=np.insert(databig,0,databig[:,0],axis=1)
            databig=np.insert(databig,0,databig[0,],axis=0)
            databig=np.insert(databig,-1,databig[-1,],axis=0)  #create a bigger array by extending the first/last col/row to outwards. 
            dataR=np.roll(databig,1,axis=1)
            dataL=np.roll(databig,-1,axis=1)
            dataU=np.roll(databig,-1,axis=0)
            dataD=np.roll(databig,1,axis=0)       #shift the data right/left/up/down
            #dataR=np.delete(np.insert(data,-1,data[:,0],axis=1),0,axis=1)
            #dataL=np.delete(np.insert(data,0,data[:,-1],axis=1),-1,axis=1)
            #dataU=np.delete(np.insert(data,-1,data[0,:],axis=0),0,axis=0)
            #dataD=np.delete(np.insert(data,0,data[-1,:],axis=0),-1,axis=0)
            dataAv=(dataR+dataL+dataU+dataD)/4.0  #avearge
            dataAv=np.delete(dataAv,0,axis=1)
            dataAv=np.delete(dataAv,-1,axis=1)
            dataAv=np.delete(dataAv,0,axis=0)
            dataAv=np.delete(dataAv,-1,axis=0) #trim the most out col/row
            bad=np.logical_and(data > tre * dataAv * factor, data > avg)
            bad_pix_loc = list(np.argwhere(bad))
            data=np.where(bad,dataAv,data)   # replace exactly the pixels reported as bad
            #print "Doing bad pixel corrections",i    
        try:
            return data, bad_pix_loc
        except:
            return data, []
        
    def sumFiles(self, data, errorData,absfac=1,absnum=None,mon=None,terms=None,tag='',gain=None):
        """Mean of the frames in ``data`` after dividing each by its monitor
        and multiplying by absfac**absnum (and by ``gain``, the monitor-gain
        factor S_ref/S of each frame, when that option is on; None: no
        factor, the legacy arithmetic exactly). With ``mon`` None the data are
        taken as already normalised; ``terms`` then gives their monitor parts
        (budget mode). ``tag`` keeps the frame keys of different sets apart."""
        if mon!=None:
            budget=self.errors.budget
            sumData=np.zeros((self.NROWS,self.NCOLS))
            sumErrorData=np.zeros((self.NROWS,self.NCOLS))
            count=0
            keys=list(data.keys())
            for i in keys:
                if gain is None:
                    sumData=sumData+data[i]*attenuation(absfac,absnum[count])/mon[count]
                    if budget:   # counting part only; the monitor part is kept per frame
                        sumErrorData=sumErrorData+errorData[i]**2/mon[count]**2*attenuation(absfac,absnum[count],2.0)
                    else:
                        sumErrorData=sumErrorData+(errorData[i]**2/mon[count]**2+data[i]**2/mon[count]**3)*attenuation(absfac,absnum[count],2.0)
                else:
                    g=gain[count]
                    sumData=sumData+data[i]*attenuation(absfac,absnum[count])/mon[count]*g
                    if budget:
                        sumErrorData=sumErrorData+errorData[i]**2/mon[count]**2*attenuation(absfac,absnum[count],2.0)*g**2
                    else:
                        sumErrorData=sumErrorData+(errorData[i]**2/mon[count]**2+data[i]**2/mon[count]**3)*attenuation(absfac,absnum[count],2.0)*g**2
                count=count+1
            self.imageData=np.array(sumData/count)
            self.errorData=np.sqrt(sumErrorData)/count
            terms_out=MonitorTerms()
            if budget:
                if count==1:   # follow the image itself (bad-pixel corrections included)
                    terms_out.add((tag,keys[0]),self.imageData,1.0,float(self.errors.monitor.relative(mon[0])))
                else:
                    for k,i in enumerate(keys):
                        terms_out.add((tag,i),data[i],attenuation(absfac,absnum[k])/mon[k]/count*(1.0 if gain is None else gain[k]),float(self.errors.monitor.relative(mon[k])))
            self.monitorTerms=terms_out
        else:
            #print 'Error:: No Monitor Counts Provided!!'
            self.imageData=data
            self.errorData=errorData
            self._setTerms(terms)
        
            
    def plotImage(self, data, errordata, absfac=1,absnum=None,  hroi=None,  vroi=None,  cen=None,  alpha=None,  s2d_dist=None, ax_type='pix', wavelength=None, min=0, max=None, cmap='gray',log=0,sh=None,fsize=16,interpolation='nearest',mon=None):
        """Plots the CCD image with give Horizontal and Vertical Region of Interests given by hroi and vroi respectively in pixels"""
        if hroi==None:
            hroi=self.hroi
        if vroi==None:
            vroi=self.vroi
        self.sumFiles(data,errordata, absfac=absfac,absnum=absnum,mon=mon)
        if np.abs(alpha)<0.001:
            sh=0
        pylab.title('Linear Intensity')
        if log!=0:
            self.imageData=pylab.log10(self.imageData)
            pylab.title('Log Intensity')
        hroi[1]=np.min(np.array([hroi[1], self.NCOLS]))
        vroi[1]=np.min(np.array([vroi[1], self.NROWS]))
        if cen==None:
            pylab.imshow(self.imageData[vroi[0]:vroi[1]+1, hroi[0]:hroi[1]+1], origin='upper', extent=[hroi[0], hroi[1], vroi[1], vroi[0]], aspect=1, vmin=min, vmax=max, cmap=cmap, interpolation=interpolation)
        else:
            if ax_type=='pix':
                x=np.arange(hroi[0], hroi[1]+1)
                y=np.arange(vroi[0], vroi[1]+1)
#            X, Y=np.meshgrid(x, y)
                pylab.xlabel(r'\textbf{Pix_X}')
                pylab.ylabel(r'\textbf{Pix_Y}')
            elif ax_type=='ang':
                x=np.arange(hroi[0]-cen[0], hroi[1]-cen[0]+1)*self.pix_size*180.0/s2d_dist/np.pi
                y=(-np.arange(vroi[0]-cen[1], vroi[1]-cen[1]+1)*self.pix_size+sh)*180.0/s2d_dist/np.pi
#                X, Y=np.meshgrid(x, y)#*pix_size*180.0/s2d_dist/np.pi
                pylab.xlabel(r'\textbf{\psi (Degrees)}')
                pylab.ylabel(r'\textbf{\theta_f (Degrees)}')
            elif ax_type=='rec':
                x=np.arange(hroi[0]-cen[0], hroi[1]-cen[0]+1)*self.pix_size/s2d_dist
                y=(-np.arange(vroi[0]-cen[1], vroi[1]-cen[1]+1)*self.pix_size-sh)/s2d_dist
                x=pylab.sin(x/2)*4*pylab.pi/wavelength
                y=(pylab.sin(y)+pylab.sin(alpha*pylab.pi/180))*2*pylab.pi/wavelength
                pylab.xlabel(r'\textbf{Q_x (\AA^{-1})}')
                pylab.ylabel(r'\textbf{Q_z (\AA^{-1})}')
            pylab.imshow(self.imageData[vroi[0]:vroi[1]+1, hroi[0]:hroi[1]+1], extent=[x[0], x[-1], y[-1], y[1]], cmap=cmap, interpolation=interpolation,vmin=min, vmax=max)
        pylab.colorbar()
        pylab.grid()
        pylab.show()


    def plotHint(self, data,errordata,absfac=1,absnum=None,  hroi=None,  vroi=None, cen=None, ax_type='Pixels', wavelength=None,s2d_dist=None,sh=None,alpha=None, truealpha=None, mon=None, terms=None, gain=None):
        """plots the Integrated Intensity along horizontal direction as a function of pixels along vertical direction"""
        if hroi==None:
            hroi=self.hroi
        if vroi==None:
            vroi=self.vroi
        self.sumFiles(data,errordata, absfac=absfac,absnum=absnum,mon=mon,terms=terms,gain=gain)
        hroi=list(map(int,hroi))
        vroi=list(map(int,vroi))
        y=np.arange(vroi[0], vroi[1]+1)  #create a array from x-axis
        hint=np.sum(self.imageData[vroi[0]:vroi[1]+1, hroi[0]:hroi[1]+1], axis=1)
        hinterr=np.sqrt(np.sum(self.errorData[vroi[0]:vroi[1]+1, hroi[0]:hroi[1]+1]**2, axis=1))
        self.hintMonitor=self._profileMonitor(np.s_[vroi[0]:vroi[1]+1, hroi[0]:hroi[1]+1], 1)
        if self.hintMonitor:
            hinterr=np.sqrt(hinterr**2+self._squares(self.hintMonitor))
        if self.det=='Pilatus':
            if ax_type=='Angles':
                y=(np.arctan((np.arange(vroi[0]-cen[1], vroi[1]-cen[1]+1)*self.pix_size)/s2d_dist)+np.arcsin(2*np.sin(alpha)-np.sin(truealpha)))*180/np.pi
            elif ax_type=='Q':
                y1=np.arctan((np.arange(vroi[0]-cen[1], vroi[1]-cen[1]+1)*self.pix_size)/s2d_dist)
                y=(np.sin(y1+np.arcsin(2*np.sin(alpha)-np.sin(truealpha)))+np.sin(truealpha))*2*pylab.pi/wavelength
        self.hintData=np.vstack((y, hint, hinterr)).transpose()

    def plotVint(self, data, errordata, absfac=1,absnum=None,  hroi=None,  vroi=None, alpha=None,dth=None, sh=None, wavelength=None, pix_size=PIXEL_MM,cen=None, s2d_dist=None,ax_type='Pixels', mon=None, terms=None, gain=None):
        """Plots the Integrated intensity along vertical direction as a function of pixels along horizontal direction"""
        if hroi==None:
            hroi=self.hroi
        if vroi==None:
            vroi=self.vroi
        self.sumFiles(data,errordata, absfac=absfac,absnum=absnum,mon=mon,terms=terms,gain=gain)
        #if np.abs(alpha)<0.001:
        #    sh=0
        hroi=list(map(int,hroi))
        vroi=list(map(int,vroi))
        x=np.arange(hroi[0], hroi[1]+1)
        vint=np.sum(self.imageData[vroi[0]:vroi[1]+1, hroi[0]:hroi[1]+1], axis=0)
        vinterr=np.sqrt(np.sum(self.errorData[vroi[0]:vroi[1]+1, hroi[0]:hroi[1]+1]**2, axis=0))
        self.vintMonitor=self._profileMonitor(np.s_[vroi[0]:vroi[1]+1, hroi[0]:hroi[1]+1], 0)
        if self.vintMonitor:
            vinterr=np.sqrt(vinterr**2+self._squares(self.vintMonitor))
        if self.det=='Pilatus':
            if ax_type=='Angles':
                x=(dth+np.arctan(np.arange(hroi[0]-cen[0], hroi[1]-cen[0]+1)*self.pix_size/s2d_dist))*180/np.pi
            elif ax_type=='Q':
                x=dth+np.arctan(np.arange(hroi[0]-cen[0], hroi[1]-cen[0]+1)*self.pix_size/s2d_dist)
                x=pylab.sin(x/2)*4*pylab.pi/wavelength
        self.vintData=np.vstack((x,vint,vinterr)).transpose()


    def _profileMonitor(self, region, axis):
        """{frame key: monitor amplitude per profile point} (budget mode)."""
        if not self.errors.budget or len(self.monitorTerms)==0:
            return {}
        return self.monitorTerms.amplitudes(region, axis=axis)

    @staticmethod
    def _squares(amps):
        return np.sum([np.square(a) for a in amps.values()], axis=0)

    def netROI(self):
        """(net, error) of the boxes of the last sumROI: S - (B1 + B2)/2.
        Legacy: sqrt(sigerr^2 + (b1err^2 + b2err^2)/4), each box error with
        its own monitor term. Budget: counting parts in quadrature, then the
        monitor amplitude of each frame on the net signal."""
        p=self.roiParts
        sig,sigerr,lbg,lbgerr,rbg,rbgerr=p['values']
        net=sig-(lbg+rbg)/2.0
        if not p['budget']:
            return net, np.sqrt(sigerr**2+(lbgerr**2+rbgerr**2)/4)
        cS,cL,cR=(c*self.errors.counting_scale for c in p['counting'])   # C63/C64: s, 1 by default
        amps=dict(p['monitor'][0])
        for key,a in p['monitor'][1].items():
            amps[key]=amps.get(key,0.0)-a/2.0
        for key,a in p['monitor'][2].items():
            amps[key]=amps.get(key,0.0)-a/2.0
        mon=float(np.sum([a*a for a in amps.values()])) if amps else 0.0
        return net, np.sqrt(cS**2+(cL**2+cR**2)/4+mon)

    def setROI(self, data,errordata, absfac=1,absnum=None, slit=[11, 11], cen=[10, 10], bg=None,dir='h',mon=None,gain=None):
        """Sets the ROI of the image file using slit size and center of the ROI and calculates the total counts in the ROI"""
        if mon!=None:
            self.sumFiles(data,errordata,absfac=absfac,absnum=absnum,mon=mon,gain=gain)
        else:
            self.imageData=data
        self.imageROI=np.array(list(self.imageData))
        max=np.max(self.imageData)*100
        slit=[slit[1], slit[0]]
        cen=[cen[1], cen[0]]
        for i in range(cen[1]-(slit[1]+1)//2,  cen[1]+(slit[1]+1)//2+1):
            self.imageROI[cen[0]-(slit[0]+1)//2, i]=max
            self.imageROI[cen[0]+(slit[0]+1)//2, i]=max
        for j in range(cen[0]-(slit[0]+1)//2,  cen[0]+(slit[0]+1)//2+1):
            self.imageROI[j, cen[1]-(slit[1]+1)//2]=max
            self.imageROI[j, cen[1]+(slit[1]+1)//2]=max
        self.sig=np.sum(self.imageData[cen[0]-(slit[0]+1)//2:cen[0]+(slit[0]+1)//2+1,  cen[1]-(slit[1]+1)//2:cen[1]+(slit[1]+1)//2+1])
        self.sigerr=np.sqrt(np.sum(self.errorData[cen[0]-(slit[0]+1)//2:cen[0]+(slit[0]+1)//2+1,  cen[1]-(slit[1]+1)//2:cen[1]+(slit[1]+1)//2+1]**2))
        if bg!=None:
            self.lbg=0
            self.lbgerr=0
            self.rbg=0
            self.rbgerr=0
            self.bbg=0
            self.bbgerr=0
            self.tbg=0
            self.tbgerr=0
            if dir=='H':
                self.bglcen=cen[1]-int(bg*slit[1])
                self.bgrcen=cen[1]+int(bg*slit[1])
                for i in range(self.bglcen-(slit[1]+1)//2,  self.bglcen+(slit[1]+1)//2+1):
                    self.imageROI[cen[0]-(slit[0]+1)//2, i]=max
                    self.imageROI[cen[0]+(slit[0]+1)//2, i]=max
                for j in range(cen[0]-(slit[0]+1)//2,  cen[0]+(slit[0]+1)//2+1):
                    self.imageROI[j, self.bglcen-(slit[1]+1)//2]=max
                    self.imageROI[j, self.bglcen+(slit[1]+1)//2]=max
                for i in range(self.bgrcen-(slit[1]+1)//2,  self.bgrcen+(slit[1]+1)//2+1):
                    self.imageROI[cen[0]-(slit[0]+1)//2, i]=max
                    self.imageROI[cen[0]+(slit[0]+1)//2, i]=max
                for j in range(cen[0]-(slit[0]+1)//2,  cen[0]+(slit[0]+1)//2+1):
                    self.imageROI[j, self.bgrcen-(slit[1]+1)//2]=max
                    self.imageROI[j, self.bgrcen+(slit[1]+1)//2]=max

                for j in range(cen[0]-(slit[0]+1)//2,  cen[0]+(slit[0]+1)//2+1):
                    for i in range(self.bglcen-(slit[1]+1)//2,  self.bglcen+(slit[1]+1)//2+1):
                        self.lbg=self.lbg+self.imageData[j, i]
                        self.lbgerr=self.lbgerr+self.errorData[j, i]**2
                    for i in range(self.bgrcen-(slit[1]+1)//2,  self.bgrcen+(slit[1]+1)//2+1):
                        self.rbg=self.rbg+self.imageData[j, i]
                        self.rbgerr=self.rbgerr+self.errorData[j, i]**2
                self.lbgerr=np.sqrt(self.lbgerr)
                self.rbgerr=np.sqrt(self.rbgerr)
            else:
                self.bgucen=cen[0]-int(bg*slit[0])
                self.bgdcen=cen[0]+int(bg*slit[0])
                for i in range(self.bgucen-(slit[0]+1)//2,  self.bgucen+(slit[0]+1)//2+1):
                    self.imageROI[i,cen[1]-(slit[1]+1)//2]=max
                    self.imageROI[i,cen[1]+(slit[1]+1)//2]=max
                for j in range(cen[1]-(slit[1]+1)//2,  cen[1]+(slit[1]+1)//2+1):
                    self.imageROI[self.bgucen-(slit[0]+1)//2,j]=max
                    self.imageROI[self.bgucen+(slit[0]+1)//2,j]=max
                for i in range(self.bgdcen-(slit[0]+1)//2,  self.bgdcen+(slit[0]+1)//2+1):
                    self.imageROI[i, cen[1]-(slit[1]+1)//2]=max
                    self.imageROI[i, cen[1]+(slit[1]+1)//2]=max
                for j in range(cen[1]-(slit[1]+1)//2,  cen[1]+(slit[1]+1)//2+1):
                    self.imageROI[self.bgdcen-(slit[0]+1)//2,j]=max
                    self.imageROI[self.bgdcen+(slit[0]+1)//2,j]=max

                for j in range(cen[1]-(slit[1]+1)//2,  cen[1]+(slit[1]+1)//2+1):
                    for i in range(self.bgucen-(slit[0]+1)//2,  self.bgucen+(slit[0]+1)//2+1):
                        self.tbg=self.tbg+self.imageData[i, j]
                        self.tbgerr=self.tbgerr+self.errorData[i, j]**2
                    for i in range(self.bgdcen-(slit[0]+1)//2,  self.bgdcen+(slit[0]+1)//2+1):
                        self.bbg=self.bbg+self.imageData[i, j]
                        self.bbgerr=self.bbgerr+self.errorData[i, j]**2
                self.tbgerr=np.sqrt(self.tbgerr)
                self.bbgerr=np.sqrt(self.bbgerr)

    def peakLocate(self,data, errordata, cen=[10,10],mon=None):  #for pilatus patch
        self.imageData=data/mon
        if self.errors.budget:
            self.errorData=np.sqrt(errordata**2/mon**2)
            self.monitorTerms=MonitorTerms()
            self.monitorTerms.add(('',0),self.imageData,1.0,float(self.errors.monitor.relative(mon)))
        else:
            self.errorData=np.sqrt(errordata**2/mon**2+data**2/mon**3)
            self.monitorTerms=MonitorTerms()
        maxserwin=3
        locwin=2
        maxserdata=self.imageData[cen[1]-maxserwin:cen[1]+maxserwin+1,cen[0]-maxserwin:cen[0]+maxserwin+1]
        maxpos=np.where(maxserdata==np.max(maxserdata))
        #print np.max(maxserdata),maxpos
        maxpix=[cen[0]+maxpos[1][0]-maxserwin, cen[1]+maxpos[0][0]-maxserwin]
        locdata=self.imageData[maxpix[1]-locwin:maxpix[1]+locwin+1,maxpix[0]-locwin:maxpix[0]+locwin+1]
        row=np.arange(maxpix[1]-locwin,maxpix[1]+locwin+1)
        col=np.arange(maxpix[0]-locwin,maxpix[0]+locwin+1)
        col,row=np.meshgrid(col,row)
        with np.errstate(invalid='ignore',divide='ignore'):
            locx=np.sum(locdata*col)/np.sum(locdata)
            locy=np.sum(locdata*row)/np.sum(locdata)
        if not (np.isfinite(locx) and np.isfinite(locy)):   # no counts about the peak (a dark frame): the brightest pixel
            return int(maxpix[0]), int(maxpix[1])           # (was: ValueError, int(NaN); found by the crash sweep 2026-11-25)
        return int(round(locx,0)), int(round(locy,0))

    def peakFind(self, data, errordata, absfac=1,absnum=None,  slit=[10, 10],  cen=[10, 10], fac=1, min=0, max=1000, bg=None, cmap='gray', dir='h',mon=None,cenfit=0,gain=None):
        self.sumFiles(data, errordata, absfac=absfac,absnum=absnum,mon=mon,gain=gain)
        slit=[slit[1], slit[0]]
        self.cen=[cen[1], cen[0]]
        fac=fac*0.5
        z=self.imageData[self.cen[0]-int(slit[0]*fac):self.cen[0]+int(slit[0]*fac)+1, self.cen[1]-int(slit[1]*fac): self.cen[1]+int(slit[1]*fac)+1]
        y=range(self.cen[0]-int(slit[0]*fac), self.cen[0]+int(slit[0]*fac)+1)
        x=range(self.cen[1]-int(slit[1]*fac), self.cen[1]+int(slit[1]*fac)+1)
        #a,b=np.histogram(z,bins=100)
        #v=b[np.argmax(a)]
        #z1=z-v
        #X,Y=np.meshgrid(x,y)
        ycen=self.cen[0]#np.floor(np.sum(z1*Y)/np.sum(z1))
        xcen=self.cen[1]#np.floor(np.sum(z1*X)/np.sum(z1))
        p=[1, xcen, slit[1]/2, ycen, slit[0]/2, np.median(z)]
        par1=np.array(p)
        self.fitflag=np.array([1,1,1,1,1,1])
        if cenfit!=0:
                self.fitflag=np.array([1,0,1,0,1,1])
        par=self.peakfit(p,x,y,z)#leastsq(self.peakRes, p, args=(x, y, z, par1),maxfev=5000)
        #print par[0]
        return par
        
    def peakfit(self, par, x,y,z):
        p0=[]
        j=0
        for flag in self.fitflag:
            if flag==1:
                p0.append(par[j])
            j=j+1
        p1=leastsq(self.peakRes,p0,args=(x,y,z,par),maxfev=5000)
        j=0
        i=0
        for flag in self.fitflag:
            if flag==1:
                par[j]=p1[0][i]
                i=i+1
            j=j+1
        return par
        
    
    def peakFun(self, x, y, p):
        X, Y=pylab.meshgrid(np.array(x,dtype=float), np.array(y,dtype=float))
        return p[0]*pylab.exp(-(X-p[1])**2/2/p[2]**2-(Y-p[3])**2/2/p[4]**2)+p[5]

    def peakRes(self, p, x, y, z, par):
        p0=par
        j=0
        i=0
        for flag in self.fitflag:
            if flag==1:
                p0[j]=p[i]
                i=i+1
            j=j+1
        self.res=z-self.peakFun(x, y, p0)
        return self.res.flatten()

        
    def badPix_corr(self, par=None, slit=[10, 10], cen=[10, 10], bad=0, bfac=1,  min=None, max=None, bg=None, cmap='gray', dir='h', plot=0):
        slit=[slit[1], slit[0]]
        cen=[cen[1], cen[0]]
        z=np.array(self.imageData[cen[0]-(slit[0]+1)//2:cen[0]+(slit[0]+1)//2+1, cen[1]-(slit[1]+1)//2: cen[1]+(slit[1]+1)//2+1])
        x=range(cen[1]-(slit[1]+1)//2, cen[1]+(slit[1]+1)//2+1)
        y=range(cen[0]-(slit[0]+1)//2, cen[0]+(slit[0]+1)//2+1)
        if plot==1:
            f=pylab.figure()
            pylab.subplots_adjust(hspace=0.4)
 #           pylab.colorbar()
            f.add_subplot(321)
            pylab.title('ROI w/o corr')
            if min==None:
                emin=np.min(z)
            else:
                emin=min
            if max==None:
                emax=np.max(z)
            else:
                emax=max
            pylab.imshow(z, extent=[x[0], x[-1], y[-1], y[0]], interpolation='nearest', vmin=emin, vmax=emax, cmap='gray')
        if par!=None:
            cen=[int(np.floor(par[3])), int(np.floor(par[1]))]
        #print cen
        z=np.array(self.imageData[cen[0]-(slit[0]+1)//2:cen[0]+(slit[0]+1)//2+1, cen[1]-(slit[1]+1)//2: cen[1]+(slit[1]+1)//2+1])
        x=range(cen[1]-(slit[1]+1)//2, cen[1]+(slit[1]+1)//2+1)
        y=range(cen[0]-(slit[0]+1)//2, cen[0]+(slit[0]+1)//2+1)
        self.peakRes(par, x, y, z,par)
        z1=self.peakFun(x, y, par)
        self.avres=np.average(self.res**2)
        (self.badpixY, self.badpixX)=np.where(self.res>bfac**bad*np.sqrt(self.avres))
        #print 'Signal----'
        self.badSig=[]
        for i in range(len(self.badpixY)):
           # print self.badpixX[i]+x[0], self.badpixY[i]+y[0],bfac**bad*np.sqrt(self.avres),  z1[self.badpixY[i], self.badpixX[i]], self.res[self.badpixY[i], self.badpixX[i]], z[self.badpixY[i],self.badpixX[i]] 
            self.badSig.append([self.badpixX[i]+x[0], self.badpixY[i]+y[0]])
        for i in range(len(self.badpixY)):
            self.errorData[self.badpixY[i]+y[0], self.badpixX[i]+x[0]]=z1[self.badpixY[i], self.badpixX[i]]*self.errorData[self.badpixY[i]+y[0], self.badpixX[i]+x[0]]/self.imageData[self.badpixY[i]+y[0], self.badpixX[i]+x[0]]
            self.imageData[self.badpixY[i]+y[0], self.badpixX[i]+x[0]]=z1[self.badpixY[i], self.badpixX[i]]
        if plot==1:
            f.add_subplot(322)
            pylab.title('ROI w corr')
#            pylab.imshow(z1, extent=[x[0], x[-1], y[-1], y[0]], interpolation='nearest', vmin=min, vmax=max, cmap='gray')
            if min==None:
                emin=np.min(self.imageData[y[0]:y[-1]+1, x[0]:x[-1]+1])
            else:
                emin=min
            if max==None:
                emax=np.max(self.imageData[y[0]:y[-1]+1, x[0]:x[-1]+1])
            else:
                emax=max
            pylab.imshow(self.imageData[y[0]:y[-1]+1, x[0]:x[-1]+1], extent=[x[0], x[-1], y[-1], y[0]], interpolation='nearest', vmin=emin, vmax=emax, cmap='gray')
        if bg!=None:
            if dir=='H':
                cenl=[cen[0], cen[1]-bg*slit[1]]
                cenl=list(map(int,  cenl))
                zleft=np.array(self.imageData[cenl[0]-(slit[0]+1)//2:cenl[0]+(slit[0]+1)//2+1, cenl[1]-(slit[1]+1)//2: cenl[1]+(slit[1]+1)//2+1])
                xleft=range(cenl[1]-(slit[1]+1)//2, cenl[1]+(slit[1]+1)//2+1)
                yleft=range(cenl[0]-(slit[0]+1)//2, cenl[0]+(slit[0]+1)//2+1)
                self.avebgleft=np.average(zleft)
                self.resbgleft=zleft-self.avebgleft
                if plot==1:
                    if min==None:
                        emin=np.min(zleft)
                    else:
                        emin=min
                    if max==None:
                        emax=np.max(zleft)
                    else:
                        emax=max
                    f.add_subplot(323)
                    pylab.title('LBG w/o corr')
                    pylab.imshow(zleft, extent=[xleft[0], xleft[-1], yleft[-1], yleft[0]], interpolation='nearest', vmin=emin, vmax=emax, cmap='gray')
                (self.badpixLY, self.badpixLX)=np.where(self.resbgleft>bfac**bad*np.sqrt(np.average(self.resbgleft**2)))
               # print 'Left BG----'
                self.badLeft=[]
                for i in range(len(self.badpixLY)):
                   # print self.badpixLX[i]+xleft[0], self.badpixLY[i]+yleft[0], bfac**bad*np.sqrt(np.average(self.resbgleft**2)),  self.resbgleft[self.badpixLY[i], self.badpixLX[i]], zleft[self.badpixLY[i],self.badpixLX[i]], self.avebgleft
                    self.badLeft.append([self.badpixLX[i]+xleft[0], self.badpixLY[i]+yleft[0]])
                for i in range(len(self.badpixLY)):
                    self.errorData[self.badpixLY[i]+yleft[0], self.badpixLX[i]+xleft[0]]=np.floor(self.avebgleft)*self.errorData[self.badpixLY[i]+yleft[0], self.badpixLX[i]+xleft[0]]/self.imageData[self.badpixLY[i]+yleft[0], self.badpixLX[i]+xleft[0]]
                    self.imageData[self.badpixLY[i]+yleft[0], self.badpixLX[i]+xleft[0]]=self.avebgleft
                if plot==1:
#                    if min==None:
#                        emin=np.min(self.imageData[yleft[0]:yleft[-1]+1, xleft[0]:xleft[-1]+1])
#                    else:
#                        emin=min
#                    if max==None:
#                        emax=np.max(self.imageData[yleft[0]:yleft[-1]+1, xleft[0]:xleft[-1]+1])
#                    else:
#                        emax=max
                    f.add_subplot(324)
                    pylab.title('LBG w corr')
                    pylab.imshow(self.imageData[yleft[0]:yleft[-1]+1, xleft[0]:xleft[-1]+1], extent=[xleft[0], xleft[-1], yleft[-1], yleft[0]], interpolation='nearest', vmin=emin, vmax=emax, cmap='gray')
                cenr=[cen[0], cen[1]+bg*slit[1]]
                cenr=list(map(int,  cenr))
                zright=np.array(self.imageData[cenr[0]-(slit[0]+1)//2:cenr[0]+(slit[0]+1)//2+1, cenr[1]-(slit[1]+1)//2: cenr[1]+(slit[1]+1)//2+1])
                xright=range(cenr[1]-(slit[1]+1)//2, cenr[1]+(slit[1]+1)//2+1)
                yright=range(cenr[0]-(slit[0]+1)//2, cenr[0]+(slit[0]+1)//2+1)
                self.avebgright=np.average(zright)
                self.resbgright=zright-self.avebgright
                if plot==1:
                    if min==None:
                        emin=np.min(zright)
                    else:
                        emin=min
                    if max==None:
                        emax=np.max(zright)
                    else:
                        emax=max
                    f.add_subplot(325)
                    pylab.title('RBG w/o corr')
                    pylab.imshow(zright, extent=[xright[0], xright[-1], yright[-1], yright[0]], interpolation='nearest', vmin=emin, vmax=emax, cmap='gray')
                (self.badpixRY, self.badpixRX)=np.where(self.resbgright>bfac**bad*np.sqrt(np.average(self.resbgright**2)))
               # print 'Right BG----'
                self.badRight=[]
                for i in range(len(self.badpixRY)):
                    #print self.badpixRX[i]+xright[0], self.badpixRY[i]+yright[0],  bfac**bad*np.sqrt(np.average(self.resbgright**2)),  self.resbgright[self.badpixRY[i], self.badpixRX[i]], zright[self.badpixRY[i],self.badpixRX[i]], self.avebgright 
                    self.badRight.append([self.badpixRX[i]+xright[0], self.badpixRY[i]+yright[0]])
                for i in range(len(self.badpixRY)):
                    self.errorData[self.badpixRY[i]+yright[0], self.badpixRX[i]+xright[0]]=np.floor(self.avebgright)*self.errorData[self.badpixRY[i]+yright[0], self.badpixRX[i]+xright[0]]/self.imageData[self.badpixRY[i]+yright[0], self.badpixRX[i]+xright[0]]
                    self.imageData[self.badpixRY[i]+yright[0], self.badpixRX[i]+xright[0]]=self.avebgright
                if plot==1:
#                    if min==None:
#                        emin=np.min(self.imageData[yright[0]:yright[-1]+1, xright[0]:xright[-1]+1])
#                    else:
#                        emin=min
#                    if max==None:
#                        emax=np.max(self.imageData[yright[0]:yright[-1]+1, xright[0]:xright[-1]+1])
#                    else:
#                        emax=max
                    f.add_subplot(326)
                    pylab.title('RBG w corr')
                    pylab.imshow(self.imageData[yright[0]:yright[-1]+1, xright[0]:xright[-1]+1], extent=[xright[0], xright[-1], yright[-1], yright[0]], interpolation='nearest', vmin=emin, vmax=emax, cmap='gray')
                    pylab.show()
                return np.sum(self.imageData[y[0]:y[-1]+1, x[0]:x[-1]+1]),np.sqrt(np.sum(self.errorData[y[0]:y[-1]+1, x[0]:x[-1]+1]**2)), np.sum(self.imageData[yleft[0]:yleft[-1]+1, xleft[0]:xleft[-1]+1]),np.sqrt(np.sum(self.errorData[yleft[0]:yleft[-1]+1, xleft[0]:xleft[-1]+1]**2)),np.sum(self.imageData[yright[0]:yright[-1]+1, xright[0]:xright[-1]+1]),np.sqrt(np.sum(self.errorData[yright[0]:yright[-1]+1, xright[0]:xright[-1]+1]**2))
            else:
                cenu=[cen[0]+bg*slit[0], cen[1]]
                cenu=list(map(int,  cenu))
                zup=self.imageData[cenu[0]-(slit[0]+1)//2:cenu[0]+(slit[0]+1)//2+1, cenu[1]-(slit[1]+1)//2: cenu[1]+(slit[1]+1)//2+1]
                xup=range(cenu[1]-(slit[1]+1)//2, cenu[1]+(slit[1]+1)//2+1)
                yup=range(cenu[0]-(slit[0]+1)//2, cenu[0]+(slit[0]+1)//2+1)
                self.avebgup=np.average(zup)
                self.resbgup=zup-self.avebgup
                if plot==1:
                    if min==None:
                        emin=np.min(zup)
                    else:
                        emin=min
                    if max==None:
                        emax=np.max(zup)
                    else:
                        emax=max
                    f.add_subplot(323)
                    pylab.title('UBG w/o corr')
                    pylab.imshow(zup, extent=[xup[0], xup[-1], yup[-1], yup[0]], interpolation='nearest', vmin=emin, vmax=emax, cmap='gray')
                (self.badpixUY, self.badpixUX)=np.where(self.resbgup>10**bad*np.sqrt(np.average(self.resbgup**2)))                
              #  print 'Upper BG----'
                self.badUp=[]
                for i in range(len(self.badpixUY)):
                    #print self.badpixUX[i]+xup[0], self.badpixUY[i]+yup[0], bfac**bad*np.sqrt(np.average(self.resbgup**2)),  self.resbgup[self.badpixUY[i], self.badpixUX[i]], zup[self.badpixUY[i],self.badpixUX[i]] 
                    self.badUp.append([self.badpixUX[i]+xup[0], self.badpixUY[i]+yup[0]])
                for i in range(len(self.badpixUY)):
                    self.errorData[self.badpixUY[i]+yup[0], self.badpixUX[i]+xup[0]]=np.floor(self.avebgup)*self.errorData[self.badpixUY[i]+yup[0], self.badpixUX[i]+xup[0]]/self.imageData[self.badpixUY[i]+yup[0], self.badpixUX[i]+xup[0]]
                    self.imageData[self.badpixUY[i]+yup[0], self.badpixUX[i]+xup[0]]=np.floor(self.avebgup)
                if plot==1:
                    if min==None:
                        emin=np.min(self.imageData[yup[0]:yup[-1]+1, xup[0]:xup[-1]+1])
                    else:
                        emin=min
                    if max==None:
                        emax=np.max(self.imageData[yup[0]:yup[-1]+1, xup[0]:xup[-1]+1])
                    else:
                        emax=max
                    f.add_subplot(324)
                    pylab.title('UBG w corr')
                    pylab.imshow(self.imageData[yup[0]:yup[-1]+1, xup[0]:xup[-1]+1], extent=[xup[0], xup[-1], yup[-1], yup[0]], interpolation='nearest', vmin=emin, vmax=emax, cmap='gray')
                cend=[cen[0]-bg*slit[0], cen[1]]
                cend=list(map(int,  cend))
                zdown=self.imageData[cend[0]-(slit[0]+1)//2:cend[0]+(slit[0]+1)//2+1, cend[1]-(slit[1]+1)//2: cend[1]+(slit[1]+1)//2+1]
                xdown=range(cend[1]-(slit[1]+1)//2, cend[1]+(slit[1]+1)//2+1)
                ydown=range(cend[0]-(slit[0]+1)//2, cend[0]+(slit[0]+1)//2+1)
                self.avebgdown=np.average(zdown)
                self.resbgdown=zdown-self.avebgdown
                if plot==1:
                    if min==None:
                        emin=np.min(zdown)
                    else:
                        emin=min
                    if max==None:
                        emax=np.max(zdown)
                    else:
                        emax=max
                    f.add_subplot(325)
                    pylab.title('DBG w/o corr')
                    pylab.imshow(zdown, extent=[xdown[0], xdown[-1], ydown[-1], ydown[0]], interpolation='nearest', vmin=emin, vmax=emax, cmap='gray')
                (self.badpixDY, self.badpixDX)=np.where(self.resbgdown>10**bad*np.sqrt(np.average(self.resbgdown**2)))
              #  print 'Down BG----'
                self.badDown=[]
                for i in range(len(self.badpixDY)):
                   # print self.badpixDX[i]+xdown[0], self.badpixDY[i]+ydown[0],  bfac**bad*np.sqrt(np.average(self.resbgdown**2)),  self.resbgdown[self.badpixDY[i], self.badpixDX[i]], zdown[self.badpixDY[i],self.badpixDX[i]] 
                    self.badDown.append([self.badpixDX[i]+xdown[0], self.badpixDY[i]+ydown[0]])
                for i in range(len(self.badpixDY)):
                    self.errorData[self.badpixDY[i]+ydown[0], self.badpixDX[i]+xdown[0]]=np.floor(self.avebgdown)*self.errorData[self.badpixDY[i]+ydown[0], self.badpixDX[i]+xdown[0]]/self.imageData[self.badpixDY[i]+ydown[0], self.badpixDX[i]+xdown[0]]
                    self.imageData[self.badpixDY[i]+ydown[0], self.badpixDX[i]+xdown[0]]=np.floor(self.avebgdown)
                if plot==1:
                    if min==None:
                        emin=np.min(self.imageData[ydown[0]:ydown[-1]+1, xdown[0]:xdown[-1]+1])
                    else:
                        emin=min
                    if max==None:
                        emax=np.max(self.imageData[ydown[0]:ydown[-1]+1, xdown[0]:xdown[-1]+1])
                        emax=max
                    f.add_subplot(326)
                    pylab.title('DBG w corr')
                    pylab.imshow(self.imageData[ydown[0]:ydown[-1]+1, xdown[0]:xdown[-1]+1], extent=[xdown[0], xdown[-1], ydown[-1], ydown[0]], interpolation='nearest', vmin=emin, vmax=emax, cmap='gray')
                    pylab.show()
                return np.sum(self.imageData[y[0]:y[-1]+1, x[0]:x[-1]+1]),np.sqrt(np.sum(self.errorData[y[0]:y[-1]+1, x[0]:x[-1]+1]**2)),np.sum(self.imageData[yup[0]:yup[-1]+1, xup[0]:xup[-1]+1]),np.sqrt(np.sum(self.errorData[yup[0]:yup[-1]+1, xup[0]:xup[-1]+1]**2)), np.sum(self.imageData[ydown[0]:ydown[-1]+1, xdown[0]:xdown[-1]+1]),np.sqrt(np.sum(self.errorData[ydown[0]:ydown[-1]+1, xdown[0]:xdown[-1]+1]**2))
        else:
            return np.sum(self.imageData[y[0]:y[-1]+1, x[0]:x[-1]+1]),np.sqrt(np.sum(self.errorData[y[0]:y[-1]+1, x[0]:x[-1]+1]**2))
            
            
    def sumROI(self, slit=[10, 10], cen=[10, 10], bg=None, cmap='gray', dir='h'):
        """Sums of the signal box and, with ``bg``, the two background boxes
        (left/right for dir 'H', up/down otherwise) of self.imageData, with
        their errors. In budget mode each box's error holds its own monitor
        term; use netROI() for the background-subtracted signal."""
        slit=[slit[1]-2, slit[0]-2]
        cen=[cen[1], cen[0]]
        def box(c0, c1):
            x=range(c1-(slit[1]+1)//2, c1+(slit[1]+1)//2+1)
            y=range(c0-(slit[0]+1)//2, c0+(slit[0]+1)//2+1)
            return np.s_[y[0]:y[-1]+1, x[0]:x[-1]+1]
        boxes=[box(cen[0], cen[1])]
        if bg!=None:
            if dir=='H':
                cenl=list(map(int, [cen[0], cen[1]-bg*slit[1]]))
                cenr=list(map(int, [cen[0], cen[1]+bg*slit[1]]))
                boxes+= [box(*cenl), box(*cenr)]
            else:
                cenu=list(map(int, [cen[0]+bg*slit[0], cen[1]]))
                cend=list(map(int, [cen[0]-bg*slit[0], cen[1]]))
                boxes+= [box(*cenu), box(*cend)]
        values=[]
        counting=[]
        monitor=[]
        budget=self.errors.budget and len(self.monitorTerms)>0
        for b in boxes:
            v=np.sum(self.imageData[b])
            e=np.sqrt(np.sum(self.errorData[b]**2))
            counting.append(e)
            if budget:
                amps=self.monitorTerms.amplitudes(b)
                monitor.append(amps)
                e=np.sqrt(e**2+float(np.sum([x*x for x in amps.values()])))
            values+= [v, e]
        self.roiParts={'values': values if len(values)==6 else values+[0.0, 0.0, 0.0, 0.0],
                       'counting': counting+[0.0]*(3-len(counting)),
                       'monitor': monitor+[{}]*(3-len(monitor)), 'budget': budget}
        return tuple(values)

    def plotROIImage(self, data,errordata,  det='Pilatus',  slit=[10, 10],  cen=[10, 10],  min=0, max=None, cmap='gray', view='closer', bg=None, dir='h',mon=None,show=1):
        """Plots the CCD image with given Region of Interest defined by hroi and vroi respectively in pixels with respect to cen"""
        self.setROI(data,errordata,slit=slit,cen=cen,bg=bg,dir=dir,mon=mon)
        if show==1:
            slit=[slit[1], slit[0]]
            cen=[cen[1], cen[0]]
            if max==None:
                max=np.max(self.imageData)
            if view=='closer':
                if bg==None:
                    pylab.imshow(self.imageROI[cen[0]-slit[0]:cen[0]+slit[0]+1, cen[1]-slit[1]:cen[1]+slit[1]+1], origin='upper', aspect=1, vmin=min, vmax=max, cmap=cmap,  extent=[ cen[1]-slit[1], cen[1]+slit[1]+1, cen[0]+slit[0]+1, cen[0]-slit[0]], interpolation='nearest')
                else:
                    if dir=='h':
                        max=np.max(self.imageData[cen[0]-slit[0]:cen[0]+slit[0]+1, self.bglcen-slit[1]:self.bgrcen+slit[1]+1])
                        pylab.imshow(self.imageROI[cen[0]-slit[0]:cen[0]+slit[0]+1, self.bglcen-slit[1]:self.bgrcen+slit[1]+1], origin='upper', aspect=1, vmin=min, vmax=max, cmap=cmap,  extent=[ self.bglcen-slit[1], self.bgrcen+slit[1]+1, cen[0]+slit[0]+1, cen[0]-slit[0]], interpolation='nearest')
                    else:
                        max=np.max(self.imageData[self.bglcen-slit[0]:self.bgrcen+slit[0]+1,cen[1]-slit[1]:cen[1]+slit[1]+1])
                        pylab.imshow(self.imageROI[self.bglcen-slit[0]:self.bgrcen+slit[0]+1,cen[1]-slit[1]:cen[1]+slit[1]+1], origin='upper', aspect=1, vmin=min, vmax=max, cmap=cmap,  extent=[ cen[1]+slit[1]+1, cen[1]-slit[1], self.bglcen-slit[0], self.bgrcen+slit[0]+1], interpolation='nearest')
            elif view=='full':
                pylab.imshow(self.imageROI, origin='upper', aspect=1, vmin=min, vmax=max, cmap=cmap, interpolation='nearest')
            pylab.colorbar()
            pylab.grid()
            pylab.show()





