"""Joining reflectivity scans: the "legacy" chain.

``join`` is the reader's ``oneDjoin`` moved here unchanged (only ``self``
removed), so that scripts and the window share one implementation.
Behaviour that is known to be questionable is kept on purpose, because
the legacy output must stay byte-identical (handoff/19, section 2.5):

* the new scan is interpolated with a cubic spline in linear intensity
  (PHYSICS_ISSUES P1);
* the scale factor's error is folded into the points (P4);
* with ``mtype='merge'`` the scaled values are written back into
  ``data2`` in place (hand-off trap T3) — pass a copy if that matters.

``mtype='fac'`` returns (factor, xmin, xmax, ymin, ymax) for previewing an
overlap; ``mtype='merge'`` returns the joined (N, 3) array.
"""
import numpy as np
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit


def polynomial(x, *p):
    return sum([p[i] * x ** i for i in range(len(p))])


def fresnel(q, qc):
    """Fresnel reflectivity without absorption; 1 for q < qc."""
    fre = []
    for qx in q:
        if qx < qc:
            fre.append(1)
        else:
            fre.append(((qx - np.sqrt(qx ** 2 - qc ** 2)) / (qx + np.sqrt(qx ** 2 - qc ** 2))) ** 2)
    return np.array(fre)


def join(data1, data2, mtype='fac'):
    """Join two reflectivity curves (columns Qz, R, sigma); see module docstring."""
    if len(data1[0])>3:   #keep only first three columns
        for i in range(len(data1[0])-3):
            data1=np.delete(data1,-1,1)
    if len(data2[0])>3:   #keep only first three columns
        for i in range(len(data2[0])-3):
            data2=np.delete(data2,-1,1)
    data1x=data1[:,0] #get qz from data1
    data1y=data1[:,1] #get ref from data1
    data2x=data2[:,0] #get qz from data2
    data2y=data2[:,1] #get ref from data2
    
   # print data1
   # print data2
    overlap2=np.where(data2x<=data1x[-1]) #create an array for where data2 having smaller qz than points in data1
    #overlap1=np.where(np.logical_and(data1x>=data2x[0],data1x<=data2x[overlap2[0][-1]])) #create an array for where data1 having larger qz than the first point in data2 and smaller qz than the last point in data2[overlap2]
    overlap1=np.where(data1x>=data2x[0])  
   # print data1x[overlap1], data2x[overlap2]
    #f=interp1d(data2x[overlap2],data2y[overlap2], kind='linear')
    f=interp1d(data2x,data2y, kind='cubic')
    if mtype=='fac':
        fac=np.sum(data1y[overlap1])/np.sum(f(data1x[overlap1]))
       # print min(np.min(data1y[overlap1]),np.min(data2y[overlap2]*fac))
        if overlap1[0][0]==0:
            overlap1[0][0]=1
        if overlap2[0][-1]==len(data2x)-1:
            overlap2[0][-1]=len(data2x)-2
        return fac, data1x[overlap1[0][0]-1],data2x[overlap2[0][-1]+1],min(np.min(data1y[overlap1[0][0]-1:]),np.min(data2y[:overlap2[0][-1]+2]*fac)),max(np.max(data1y[overlap1[0][0]-1:]),np.max(data2y[:overlap2[0][-1]+2]*fac))
        
    elif mtype=='merge':
        data1yerr=data1[:,2] #get error from data1
        data2yerr=data2[:,2] #get error from data2
        #ferr=interp1d(data2x[overlap2],data2yerr[overlap2], kind='linear')
        ferr=interp1d(data2x,data2yerr, kind='cubic')
        x=data1x[overlap1]
        y=data1y[overlap1]/f(x)
        yerr=y*np.sqrt(((data1yerr[overlap1]/data1y[overlap1])**2+(ferr(x)/f(x))**2))
        pfit,pcov=curve_fit(polynomial,x,y,p0=[1],sigma=yerr) #fit the data with the scale factor 
        fac=pfit[0]
        facerr=pcov[0][0]**0.5
        data2y=data2y*fac           #scale data2 with the fac and facerr
        data2yerr=np.sqrt(data2yerr**2*fac**2+data2y**2*facerr**2/fac**2)
        data2[:,1]=data2y  #this also changed the data self.scanqzframe[self.pilrefsort[self.pilreforder+1]]
        data2[:,2]=data2yerr
        data=data1[:overlap1[0][0],:] #get the first part of merged data from data1
        #f2=interp1d(data2x[overlap2],data2y[overlap2], kind='linear')
        #f2err=interp1d(data2x[overlap2],data2yerr[overlap2], kind='linear')
        f2=interp1d(data2x,data2y, kind='cubic')
        f2err=interp1d(data2x,data2yerr, kind='cubic')
        data3y=f2(data1x[overlap1])   #interpolate the data2 after the scaling
        data3yerr=f2err(data1x[overlap1])
        for i in range(overlap1[0][0],overlap1[0][-1]+1): #get the second part of merged data from data2
            data=np.vstack((data,(data1x[i], (data1y[i]+data3y[i-overlap1[0][0]])/2.0,np.sqrt(data1yerr[i]**2+data3yerr[i-overlap1[0][0]]**2)/2.0)))
        if data1x[-1]>=data2x[-1]:  #part 3 patching
            datalast=data1[overlap1[0][-1]+1:,:]
        else:
            datalast=data2[overlap2[0][-1]+1:,:]
        data=np.vstack((data,datalast))
    
        return data
