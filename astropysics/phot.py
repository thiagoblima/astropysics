#Copyright (c) 2008 Erik Tollerud (etolleru@uci.edu) 
"""
This module is for observed or synthetic photometry and 
related operations.

Tends to be oriented towards optical techniques.
"""

from __future__ import division
from math import pi
import numpy as np

#photometric band centers - B&M
bandwl={'U':3650,'B':4450,'V':5510,'R':6580,'I':8060,'u':3520,'g':4800,'r':6250,'i':7690,'z':9110}

#<---------------------Classes------------------------------------------------->

class Band(object):
    """
    This class is the base of all photometric band objects
    
    subclasses should set the following arrays:
    self._x (wavelength)
    self._S (maximum should be 1)
    
    It is recommended that subclasses set the following values (otherwise they will be calculated on first access):
    self._cenwl (center of the band)
    self._widthwl (second moment of the band)
    """
    def __init__(self):
        raise NotImplementedError
    
    _cenwl = None
    @property
    def center(self):
        """
        The center of the band
        """
        if self._cenwl is None:
            raise NotImplementedError
            self._cenwl = cen
        else:
            return self._cenwl
    
    _widthwl = None
    @property
    def width(self):
        """
        second centralized moment of the band
        """
        if self._widthwl is None:
            raise NotImplementedError
            self._widthwl = wid
        else:
            return self._widthwl
    
    @property
    def lamb(self):
        """
        wavelengths for the band
        """
        return self._x
    
    @property
    def response(self):
        """
        response function - e.g. probability a photon will be detected
        """
        return self.norm*self._S
    
    norm = 1

class GaussianBand(Band):
    def __init__(self,center,width,sigs=6,n=100):
        """
        center is the central wavelength of the band, while width is the sgima 
        (if positive) or FWHM (if negative)
        """
        self._cenwl = center
        self._widthwl = sig = width if width > 0 else -width*(8*np.log(2))**-0.5#TODO:*?
        
        self._x = np.linspace(-sigs,sigs,n)*width+center
        xp = x - center
        self._S = np.exp(-xp*xp/2/sig/sig)
        
class FileBand(Band):
    def __init__(self,fn,type=None):
        """
        type can be 'txt', or 'fits', or inferred from extension
        
        if txt, first column should be lambda, second should be response
        """
        from os import path
        
        if type is None:
            ext = path.splitext(fn)[-1].lower()
            if ext == 'fits' or ext == 'fit':
                type = 'fits'
            else:
                type = 'txt'
        
        if type == 'txt':
            x,S = np.loadtxt(fn).T
        elif type == 'fits':
            import pyfits
            f = pyfits.open(fn)
            try:
                #TODO: much smarter/WCS
                x,S = f[0].data
            finally:
                f.close()
        else:
            raise ValueError('unrecognized type')
        
        

#<---------------------Procedural/utility functions---------------------------->
    
def UBVRI_to_ugriz(U,B,V,R,I,ugrizprimed=False):
    """
    transform UBVRcIc magnitudes to ugriz magnitudes as per Jester et al. (2005)
    """
    if not ugrizprimed:
        umg    =    1.28*(U-B)   + 1.13  
        #gmr    =    1.02*(B-V)   - 0.22  
        rmi    =    0.91*(R-I) - 0.20 
        rmz    =    1.72*(R-I) - 0.41
        g      =    V + 0.60*(B-V) - 0.12 
        r      =    V - 0.42*(B-V) + 0.11
        

    else:
        raise NotImplementedError
    
    return umg+g,g,r,r-rmi,r-rmz
    
def ugriz_to_UBVRI(u,g,r,i,z,ugrizprimed=False):
    """
    transform ugriz magnitudes to UBVRcIc magnitudes as per Jester et al. (2005)
    (note that z is unused)
    """
    if not ugrizprimed:
        UmB    =    0.78*(u-g) - 0.88 
        #BmV    =    0.98*(g-r) + 0.22 
        VmR    =    1.09*(r-i) + 0.22
        RmI  =    1.00*(r-i) + 0.21
        B      =    g + 0.39*(g-r) + 0.21
        V      =    g - 0.59*(g-r) - 0.01 

    else:
        raise NotImplementedError
    
    return UmB+B,B,V,V-VmR,V-VmR-RmI

def transform_dict_ugriz_UBVRI(d,ugrizprimed=False):
    ugriz = 'u' in d or 'g' in d or 'r' in d or 'i' in d or 'z' in d
    UBVRI = 'U' in d or 'B' in d or 'V' in d or 'R' in d or 'I' in d
    if ugriz and UBVRI:
        raise ValueError('both systems already present')
    if ugriz:
        u=d['u'] if 'u' in d else 0
        g=d['g'] if 'g' in d else 0
        r=d['r'] if 'r' in d else 0
        i=d['i'] if 'i' in d else 0
        z=d['z'] if 'z' in d else 0
        U,B,V,R,I=ugriz_to_UBVRI(u,g,r,i,z,ugrizprimed)
        if 'g' in d and 'r' in d:
            d['B']=B
            d['V']=V
            if 'u' in d:
                d['U']=U
            if 'i' in d and 'z' in d:
                d['I']=I
                d['R']=R
        else:
            raise ValueError('need g and r to do anything')
        
    if UBVRI:
        U=d['U'] if 'U' in d else 0
        B=d['B'] if 'B' in d else 0
        V=d['V'] if 'V' in d else 0
        R=d['R'] if 'R' in d else 0
        I=d['I'] if 'I' in d else 0
        u,g,r,i,z=UBVRI_to_ugriz(U,B,V,R,I,ugrizprimed)
        if 'B' in d and 'V' in d:
            d['g']=g
            d['r']=r
            if 'U' in d:
                d['u']=u
            if 'R' in d and 'I' in d:
                d['i']=i
                d['z']=z
        else:
            raise ValueError('need B and V to do anything')

def M_star_from_mags(B,V,R,I,color='B-V'):
    """
    uses Bell&DeJong 01 relations
    color can either be a 'B-V','B-R','V-I', or 'mean'
    returns stellar mass as mean,(B-derived,V-derived,R-derived,I-derived)
    """    
    if color=='B-V':
        c=B-V
        mlrb=10**(-0.994+1.804*c)
        mlrv=10**(-0.734+1.404*c)
        mlrr=10**(-0.660+1.222*c)
        mlri=10**(-0.627+1.075*c)
    elif color=='B-R':
        c=B-R
        mlrb=10**(-1.224+1.251*c)
        mlrv=10**(-0.916+0.976*c)
        mlrr=10**(-0.820+0.851*c)
        mlri=10**(-0.768+0.748*c)
    elif color=='V-I':
        c=V-I
        mlrb=10**(-1.919+2.214*c)
        mlrv=10**(-1.476+1.747*c)
        mlrr=10**(-1.314+1.528*c)
        mlri=10**(-1.204+1.347*c)
    elif color=='mean':
        bv=M_star_from_mags(B,V,R,I,'B-V')
        br=M_star_from_mags(B,V,R,I,'B-R')
        vi=M_star_from_mags(B,V,R,I,'V-I')
        return np.mean((bv[0],br[0],vi[0])),np.mean((bv[1],br[1],vi[1]),axis=0)
    else:
        raise ValueError('Unknown color')
    
    mstar=[]
    mstar.append(mag_to_lum(B,'B')*mlrb)
    mstar.append(mag_to_lum(V,'V')*mlrv)
    mstar.append(mag_to_lum(R,'R')*mlrr)
    mstar.append(mag_to_lum(I,'I')*mlri)
    
    return np.mean(mstar),tuple(mstar)


def distance_modulus(x,intype='distance',dx=None,autocosmo=True):
    """
    compute the distance modulus given  a distance or redshift
    
    for H=0/False/None, will treat z as a distance in pc, otherwise, redshift
    will be used with hubble relation
    
    autocosmo determines if the cosmological calculation should be
    automatically performed for z > 0.1 . if False, the only the basic
    calculation will be done.  if 'warn,' a warning will be issued
    """
    from .coords import cosmo_z_to_dist
    from .constants import H0,c
    
    c=c/1e5 #km/s
    cosmo=False
    
    if intype == 'distance':
        z=x/1e6*H0/c
        if dx is not None:
            dz = dx/1e6*H0/c
        else:
            dz = None
    elif intype == 'redshift':
        z=x
        x=z*c/H0
        if dx is not None:
            dz = dx
            dx = dz*c/H0
        else:
            dz = None
    else:
        raise ValueError('unrecognized intype')
    
    if autocosmo and np.any(z) > 0.1:
        if autocosmo == 'warn':
            from warnings import warn
            warn('redshift < 0.1 - cosmological calculation should be used')
        else:
            cosmo=True
    if cosmo:
        return cosmo_z_to_dist(z,dz,4)
    elif dx is None:
        return 5*np.log10(x)-5
    else:
        dm = 5*np.log10(x)-5
        ddm = 5*dx/x/np.log(10)
        return dm,ddm,ddm
    
def distance_from_modulus(dm):
    """
    compute the distance given the specified distance modulus.  Currently
    non-cosmological
    """
    return 10**(1+dm/5.0)
    

def abs_mag(appmag,x,intype='distance',autocosmo=True):
    """
    computes absolute magnitude from apparent magnitude and distance.
    See astro.phot.distance_modulus for details on arguments
    """
    from operator import isSequenceType
    if isSequenceType(appmag):
        appmag=np.array(appmag)
    
    distmod = distance_modulus(x,intype,None,autocosmo)
    return appmag-distmod

def app_mag(absmag,x,intype='distance',autocosmo=True):
    """
    computes apparent magnitude from absolute magnitude and distance.
    See astro.phot.distance_modulus for details on arguments
    """
    from operator import isSequenceType
    if isSequenceType(absmag):
        absmag=np.array(absmag)
        
    distmod = distance_modulus(x,intype,None,autocosmo)
    return absmag+distmod

def rh_to_surface_brightness(totalm,rh):
    """
    Compute the surface brightness given a half-light radius in arcsec.  Note
    that the totalm is the integrated magnitude, not just the half-light
    """
    return area_to_surface_brightness(totalm+2.5*np.log10(2),pi*rh*rh)

def area_to_surface_brightness(m,area):
    """
    Compute the surface brightness given a particular magnitude and area in 
    mag/sq arc seconds
    """
    return m+2.5*np.log10(area)

##Bell&DeJong & Blanton 03
#_band_to_msun={'B':5.47,
#               'V':4.82,
#               'R':4.46,
#               'I':4.14,
#               'K':3.33,
#               'u':6.80,
#               'g':5.45,
#               'r':4.76,
#               'i':4.58,
#               'z':4.51}

#B&M and http://www.ucolick.org/~cnaw/sun.html
_band_to_msun={'U':5.61,
               'B':5.48,
               'V':4.83,
               'R':4.42,
               'I':4.08,
               'J':3.64,
               'H':3.32,
               'K':3.28,
               'u':6.75,
               'g':5.33,
               'r':4.67,
               'i':4.48,
               'z':4.42}
               
def mag_to_lum(M,Mzpt=4.83,Lzpt=1,Merr=None):
    """
    calculate a luminosity from a magnitude
    
    input M can be either a magnitude value, a sequence/array of magnitudes, or
    a dictionary where the keys will be interpreted as specifying the bands  
    (e.g. they can be 'U','B','V', etc. to be looked up as described 
    below or a value for the zero-point)
    
    if Merr is given, will return (L,dL)
    
    Mzpt specifies the magnitude that matches Lzpt, so Lzpt is a unit conversion
    factor for luminosity - e.g. 4.64e32 for ergs in V with solar zero points,
    or 1 for solar
    
    Mzpt can also be 'U','B','V','R','I','J','H', or 'K' and will use B&M values 
    for solar magnitudes or 'u','g','r','i', or 'z' from http://www.ucolick.org/~cnaw/sun.html
    """
    from operator import isMappingType,isSequenceType
    
    dictin = isMappingType(M)    
    if dictin:
        dkeys = Mzpt = M.keys()
        M = M.values()
    elif type(M) is not np.ndarray:
        M=np.array(M)
        
    if type(Mzpt) == str:
        Mzpt=_band_to_msun[Mzpt]
    elif isSequenceType(Mzpt):    
        Mzpt=np.array(map(lambda x:_band_to_msun.get(x,x),Mzpt))
        
    L=(10**((Mzpt-M)/2.5))*Lzpt
    
    if dictin:
        L = dict([t for t in zip(dkeys,L)])
    
    if np.any(Merr):
        dL=Merr*L/1.0857362047581294 #-1.0857362047581294 = -2.5/ln(10)
        return L,dL
    else:
        return L

def lum_to_mag(L,Mzpt=4.83,Lzpt=1,Lerr=None):
    """
    calculate a magnitude from a luminosity
    
    see mag_to_lum() for syntax details
    """
    from operator import isMappingType,isSequenceType
        
    dictin = isMappingType(L)    
    if dictin:
        dkeys = Mzpt = L.keys()
        L = L.values()
    elif type(L) is not np.ndarray:
        L=np.array(L)     
        
    if type(Mzpt) == str:
        Mzpt=_band_to_msun[Mzpt]
    elif isSequenceType(Mzpt):    
        Mzpt=np.array(map(lambda x:_band_to_msun.get(x,x),Mzpt))
        
    M=Mzpt-2.5*np.log10(L/Lzpt)

    if dictin:
        M = dict([t for t in zip(dkeys,M)])

    if np.any(Lerr):
        dM=1.0857362047581294*Lerr/L #-1.0857362047581294 = -2.5/ln(10)
        return M,dM
    else:
        return M
    
def intensities_to_sig(Is,In,exposure=1,area=1):
    """
    converts photon count intensities (i.e. photon cm^-2 sr^-1) to signficance
    values from poisson statistics.
    
    Is is intensity of the signal
    In is intensity of the background
    """
    return exposure*area*Is*(exposure*area*(Is+In))**-0.5
    
def cosmo_surface_brightness_correction(Sobs,z,mag=True):
    """
    computes
    
    mag determines if mag/as^2 is used or if False, flux
    """
    if mag:
        return Sobs-10*np.log10(1+z)
    else:
        return Sobs*(1+z)**4
    
def kcorrect(mags,zs,magerr=None,filterlist=['U','B','V','R','I']):
    """
    Uses the Blanton et al. 2003 k-correction
    
    requires pidly (http://astronomy.sussex.ac.uk/~anthonys/pidly/) and IDL with
    kcorrect installed
    
    input magnitudes should be of dimension (nfilter,nobj), as should magerr
    zs should be sequence of length nobj
    if magerr is None, 
    
    returns absmag,kcorrections,chi2s
    """
    from .constants import H0
    import pidly
    idl=pidly.IDL()
    idl('.com kcorrect')
    #TODO: figure out if it worked
    
    mags = np.array(mags,copy=False)
    zs = np.array(zs,copy=False).ravel()
    if magerr is None:
        magerr = np.ones_like(mags)
    else:
        magerr = np.array(magerr,copy=False)
    
    if mags.shape[0] != len(filterlist) or magerr.shape[0] != len(filterlist):
        raise ValueError("number of filters and magnitude shapes don't match")
    if mags.shape[1] != zs.size or magerr.shape[1] != zs.size:
        raise ValueError("number of redshifts doesn't match magnitude shapes")
        
    fd = {'U':'bessell_U.par',
          'B':'bessell_B.par',
          'V':'bessell_V.par',
          'R':'bessell_R.par',
          'I':'bessell_I.par',
          'u':'sdss_u0.par',
          'g':'sdss_g0.par',
          'r':'sdss_r0.par',
          'i':'sdss_i0.par',
          'z':'sdss_z0.par'}    
    
    filterlist = [fd.get(fl,fl) for fl in filterlist]
    
    try:
        idl.mags = mags
        idl.magerr = magerr
        idl.zs = zs
        idl.flst = filterlist
        idl('kcorrect,mags,magerr,zs,kcorr,absmag=absmag,chi2=chi2,filterlist=flst,/magnitude,/stddev')
        #idl.pro('kcorrect',mags,magerr,zs,'kcorr',absmag='absmag',chi2='chi2',filterlist=filterlist,magnitude=True,stddev=True,)
        
        kcorr = idl.kcorr
        absmag = idl.absmag +5*np.log10(H0/100)
        chi2 = idl.chi2    
        
        return absmag,kcorr,chi2
        
    finally:
        idl.close()
        
    
        
    
