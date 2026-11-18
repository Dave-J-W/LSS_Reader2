"""Pinhole frames of SPEC scans for lss_core.pinhole, from the header as the
window reads it (c0 = columns − 1 − DBPos[1], S1v = S1T + S1B). Reads only."""
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
from lss_core.experiment import Experiment
from lss_core.images import read_pilatus
from lss_core import pinhole as ph

def frames_for(spec, scans):
    e=Experiment(spec); out=[]
    for f in e.frames(scans):
        p=e.scans[f.scan].parameters; c=e.scans[f.scan].columns
        r=read_pilatus(f.path); a=np.asarray(r[0] if isinstance(r,tuple) else r,float)
        wl=p['Wavelength']; alpha_q=math.asin(f.qz*wl/4/math.pi); at=p['In_Rot']*math.pi/180
        g=ph.FrameGeometry(dth=c['Det_Th'][f.index]*math.pi/180, alpha=at, beta0=math.asin(2*math.sin(alpha_q)-math.sin(at)),
            c0=a.shape[1]-1-p['DBPos'][1], r0=p['DBPos'][0], d_sample=p['S2D_Dist'], d_pinhole=p['S7D_Dist'], g_l3=p['g_l3'], wavelength=wl)
        out.append(ph.PinholeFrame(a, f.monitor, g, (p['S1L']+p['S1R'], p['S1T']+p['S1B'], p['S4L']+p['S4R'], at, p['S2D_Dist'], p['S7D_Dist']),
            (p['S5L'],p['S5R']), p['g_l2']-p['g_l1'], f.scan))
    return out

