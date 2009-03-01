#Copyright (c) 2008 Erik Tollerud (etolleru@uci.edu) 
"""
This module is for observed or synthetic photometry and 
related operations.

Tends to be oriented towards optical techniques.
"""

from __future__ import division
from math import pi
import numpy as np

from .spec import HasSpecUnits
try:
    #requires Python 2.6
    from abc import ABCMeta
    from abc import abstractmethod
    from abc import abstractproperty
except ImportError: #support for earlier versions
    abstractmethod = lambda x:x
    abstractproperty = property
    ABCMeta = type


#<---------------------Classes------------------------------------------------->

class Band(HasSpecUnits):
    """
    This class is the base of all photometric band objects.  Bands are expected
    to be immutable once created except for changes of units.
    
    subclasses must implement the following functions:
    *__init__ : initialize the object
    *_getCen : return the center of band 
    *_getFWHM : return the FWHM of the band
    *_getx: return an array with the x-axis
    *_getS: return the photon sensitivity (shape should match x)
    
    #the following can be optionally overriden:
    *alignBand(x): return the sensitivity of the Band interpolated to the 
                   provided x-array
    *alignToBand(x,S): return the provided sensitivity interpolated onto the 
                       x-array of the Band
    """
    __metaclass__ = ABCMeta
    
    #set default units to angstroms
    _phystype = 'wavelength'
    _unit = 'angstrom'
    _scaling = 1e-8
    
    @abstractmethod
    def __init__(self):
        raise NotImplementedError
    
    @abstractmethod
    def _getCen(self):
        raise NotImplementedError
    
    @abstractmethod
    def _getFWHM(self):
        raise NotImplementedError
    
    @abstractmethod
    def _getx(self):
        raise NotImplementedError
    
    @abstractmethod
    def _getS(self):
        raise NotImplementedError
    
    #comparison operators TODO:unit matching
    def __eq__(self,other):
        try:
            return np.all(self.x == other.x) and np.all(self.S == other.S)
        except:
            return False
    def __ne__(self,other):
        return not self.__eq__(other)
    def __lt__(self,other):
        try:
            return self.cen < other.cen
        except:
            return NotImplemented
    def __le__(self,other):
        try:
            return self.cen <= other.cen
        except:
            return NotImplemented
    def __gt__(self,other):
        try:
            return self.cen > other.cen
        except:
            return NotImplemented
    def __ge__(self,other):
        try:
            return self.cen >= other.cen
        except:
            return NotImplemented
    
    def __interp(self,x,x0,y0,interpolation):
        """
        interpolate the function defined by x0 and y0 onto the coordinates in x
        
        see Band.alignBand for interpolation types/options
        """
        if interpolation == 'linear':
            return np.interp(x,x0,y0)
        elif interpolation == 'spline':
            raise NotImplementedError
            if not hasattr(self,'_splineobj'):
                self._splineobj = None
        else:
            raise ValueError('unrecognized interpolation type')
    
    #units support
    def _unitGetX(self):
        return self._getx()
    def _unitSetX(self,val):
        raise NotImplementedError
    def _unitGetY(self):
        return self._getS()
    def _unitSetY(self,val):
        raise NotImplementedError
    
    cen = property(lambda self:self._getCen())
    FWHM = property(lambda self:self._getFWHM())
    x = property(lambda self:self._getx())
    S = property(lambda self:self._getS())
    def _getSrc(self):
        if not hasattr(self._src):
            from .objcat import Source
            self._src = Source(None)
        return self._src
    def _setSrc(self,val=None):
        from .objcat import Source
        self._src = Source(val)
    source = property(_getSrc,_setSrc)
    def _getName(self):
        if self._name is None:
            return 'Band@%4.4g'%self.cen
        else:
            return self._name
    def _setName(self,val):
        self._name = val
    name = property(_getName,_setName)
    _name = None #default is nameless
    
    zeropoint = 0 #zeropoint can be freely modified
    
    #TODO:units on alignment!
    def alignBand(self,x,interpolation='linear'):
        """
        interpolates the Band sensitivity onto the provided x-axis
        
        x can either be an array with the wanted x-axis or a ``Spectrum``
        
        interpolation can be 'linear' or 'spline'
        """
        if hasattr(x,'x') and hasattr(x,'flux'):
            x = x.x
        return self.__interp(x,self.x,self.S,interpolation)
        
    def alignToBand(self,*args,**kwargs):
        """
        interpolates the provided function onto the Band x-axis
        
        args can be:
        *alignToBand(arr): assume that the provided sequence fills the band and
        interpolate it onto the band coordinates
        *alignToBand(specobj): if specobj is of type ``Spectrum``, the ``Spectrum``
        will flux will be returned aligned to the band
        *alignToBand(x,y): the function with coordinates (x,y) will be aligned
        to the Band x-axis
        
        keywords:
        *interpolation:see Band.alignBand for interpolation types/options
        """
        if len(args) == 1:
            from operator import isSequenceType
            from .spec import Spectrum
            
            specin = args[0]
            
            if isSequenceType(specin):
                y = np.array(specin,copy=False)
                x = np.linspace(self.x[0],self.x[-1])
            elif hasattr(specin,'x') and hasattr(specin,'flux'):
                x = specin.x
                y = specin.flux
        elif len(args) == 2:
            x,y = args
        else:
            raise TypeError('alignToBand() takes 1 or 2 arguments')
        
        if 'interpolation' not in kwargs:
            kwargs['interpolation'] = 'linear'
            
        return self.__interp(self.x,x,y,kwargs['interpolation'])
    
    def computeFlux(self,spec,interpolation='linear',aligntoband=None):
        """
        compute the flux in this band for the supplied Spectrum
        
        the Spectrum is aligned to the band if aligntoband is True, or vice 
        versa, otherwise, using the specified interpolation (see Band.alignBand
        for interpolation options).  If aligntoband is None, the higher of the
        two resolutions will be left unchanged 
        """
        from scipy.integrate import simps as integralfunc
        from .constants import c
        
        if aligntoband is None:
            aligntoband = self.x.size > spec.x.size
        
        if aligntoband:
            x = self.x
            y = self.S*self.alignToBand(spec.x,spec.flux,interpolation=interpolation)
            if 'wavelength' in self.unit:
                y/=(x*c)
            else:
                y*=x
                #TODO:check energy factor
        else:
            x = spec.x
            y = self.alignBand(spec)*spec.flux
            if 'wavelength' in spec.unit:
                y/=(x*c)
            else:
                y*=x
                #TODO:check energy factor
        return integralfunc(y,x)
    
    def computeMag(self,*args,**kwargs):
        """
        Compute the magnitude of the supplied Spectrum in this band using the 
        band's ``zeropoint`` attribute
        
        args and kwargs are the same as those for computeFlux
        """
        flux = self.computeFlux(*args,**kwargs)
        return -2.5*np.log10(flux)-self.zeropoint
    
    def computeZptFromSpectrum(self,*args,**kwargs):
        """
        use the supplied Spectrum as a zero-point Spectrum to 
        define the zero point of this band
        
        args and kwargs are the same as those for computeFlux
        """
        self.zeropoint = 0
        mag = self.computeMag(*args,**kwargs)
        self.zeropoint = mag
    
    def plot(self,spec=None,**kwargs):
        """
        this plots the requested band and passes kwargs into matplotlib.pyplot.plot
        OR
        if spec is provided, the spectrum will be plotted along with the band and 
        the convolution
        
        other kwargs:
        *clf : clear the figure before plotting
        *leg : show legend where appropriate
        """
        from matplotlib import pyplot as plt
        band = self
        
        if kwargs.pop('clf',True):
                plt.clf()
                
        if spec:
            from .spec import Spectrum
            if not isinstance(spec,Spectrum):
                raise ValueError('input not a Spectrum')
            N = np.max(spec.flux)
            convflux = band.alignToBand(spec)*band.S
            
            plt.plot(band.x,N*band.S,c='k',label='$S_{\\rm Band}$')
            plt.plot(spec.x,spec.flux,c='g',ls=':',label='$f_{\\rm spec}$')
            plt.plot(band.x,convflux,c='b',ls='--',label='$f_{\\rm spec}S_{\\rm Band}$')
            
            plt.ylabel('Spec flux or S*max(spec)')
            if kwargs.pop('leg',True):
                plt.legend(loc=0)
        else:
            plt.plot(band.x,band.S,**kwargs)
            plt.ylabel('$S$')
            plt.ylim(0,band.S.max())
        plt.title('' if self.name is None else self.name)
        plt.xlabel('$\\lambda$')
        
def plot_band_group(bandgrp,**kwargs):
    """
    this will plot a group of bands on the same plot
    
    group can be a sequnce of bands, strings or a dictionary mapping names to
    bands
    
    kwargs go into Band.plot except for:
    *clf : clear figure before plotting
    *leg : show legend with band names
    *unit : unit to use on plots (defaults to angstroms)
    *c : (do not use)
    *spec : (do not use)
    """
    from matplotlib import pyplot as plt
    from operator import isMappingType,isSequenceType
    
    
    
    if isMappingType(bandgrp):
        names = bandgrp.keys()
        bs = bandgrp.values()
    else:
        names,bs = [],[]
        for b in bandgrp:
            if type(b) is str:
                names.append(b)
                bs.append(bands[b])
            else:
                names.append(b.name)
                bs.append(b)
    d = dict([(n,b) for n,b in  zip(names,bs)])
    sortednames = sorted(d,key=d.get)
    
    clf = kwargs.pop('clf',True)
    leg = kwargs.pop('leg',True)
    kwargs.pop('spec',None)
    cs = kwargs.pop('c',None)
    unit = kwargs.pop('unit','wl')
        
    try:
        oldunits = [b.unit for b in bs]
        for b in bs:
            b.unit = unit
    except NotImplementedError:
        pass
    
    
    if clf:
        plt.clf()
    
    bluetored = 'wavelength' in bs[0].unit
    
    if cs is None:
        
        x = np.arange(len(bs))
        b = 1-x*2/(len(x)-1)
        g = 1-2*np.abs(0.5-x/(len(x)-1))
        g[g>0.5] = 0.5
        r = (x*2/(len(x)-1)-1)
        r[r<0] = b[b<0] = 0
        
        if not bluetored:
            b,r = r,b
        cs = np.c_[r,g,b]
        
        #custom coloring for UBVRI and ugriz
        if len(sortednames) == 5:
            if sortednames[:3] == ['U','B','V']:
                cs = ['c','b','g','r','m']
            elif np.all([(n in sortednames[i]) for i,n in enumerate(('u','g','r','i','z'))]):
                cs = ['c','g','r','m','k']
        
    
    kwargs['clf'] = False
    for n,c in zip(sortednames,cs):
        print n,c
        kwargs['label'] = n
        kwargs['c'] = c
        d[n].plot(**kwargs)
    
    if leg:
        plt.legend(loc=0)
    
    try:
        for u,b in zip(oldunits,bs):
            b.unit = u
    except (NameError,NotImplementedError),e:
        pass
    

class GaussianBand(Band):
    def __init__(self,center,width,A=1,sigs=6,n=100,unit='angstroms',name=None):
        """
        center is the central wavelength of the band, while width is the sigma 
        (if positive) or FWHM (if negative)
        """
        self._cen = center
        self._sigma = width if width > 0 else -width*(8*np.log(2))**-0.5
        self._fwhm = self._sigma*(8*np.log(2))**0.5
        self._A = A
        
        self._n = n
        self._sigs = sigs
        self._updateXY(self._cen,self._sigma,self._A,self._n,self._sigs)
        
        HasSpecUnits.__init__(self,unit)
        
        self.name = name
        
    def _updateXY(self,mu,sigma,A,n,sigs):
        self._x = np.linspace(-sigs*sigma,sigs*sigma,n)+mu
        xp = (self._x-mu)/sigma
        self._y = A*np.exp(-xp*xp/2)
        
    def _getSigs(self):
        return self._sigs
    def _setSigs(self,val):
        self._updateXY(self._cen,self._sigma,self._A,self._n,val)
        self._sigs = val
    sigs = property(_getSigs,_setSigs)
    
    def _getn(self):
        return self._n
    def _setn(self,val):
        self._updateXY(self._cen,self._sigma,self._A,val,self._sigs)
        self._n = val
    n = property(_getn,_setn)

    @property
    def sigma(self):
        return self._sigma
    
    def _getCen(self):
        return self._cen
    
    def _getFWHM(self):
        return self._fwhm #=sigma*(8*log(2))**0.5
    
    def _getx(self):
        return self._x
    
    def _getS(self):
        return self._y
    
    def alignBand(self,x):
        xp = (x-self._cen)/self._sigma 
        return self._A*np.exp(-xp*xp/2)
        
class ArrayBand(Band):
    def __init__(self,x,S,copyonaccess=True,normalized=True,unit='angstroms',name=None):
        """
        generate a Band from a supplied quantum (e.g. photonic) response 
        function 
        
        if the response function is ever negative, the band will be offset so
        that the lowest point is 0 .  If the band x-axis is not sorted, it 
        will be sorted from lowest to highest.
        """
        self._x = np.array(x,copy=True)
        self._S = np.array(S,copy=True)
        sorti = np.argsort(self._x)
        self._x,self._S = self._x[sorti],self._S[sorti]

        if self._x.shape != self._S.shape or len(self._x.shape) != 1:
            raise ValueError('supplied x and S are not matching 1D arrays')
        if self._S.min() < 0:
            self._S -= self._S.min()
        self._N = self._S.max()
        if normalized:
            self._S /= self._N
        self.copyonaccess = copyonaccess
        self._norm = normalized
        
        self._computeMoments()
        
        HasSpecUnits.__init__(self,unit)
        
        self.name = name
        
    def _computeMoments(self):
        from scipy.integrate import  simps as integralfunc
        #trapz vs. simps: trapz faster by factor ~5,simps somewhat more accurate
        x=self._x
        y=self._S/self._S.max()
        N=1/integralfunc(y,x)
        yn = y*N #normalize so that overall integral is 1
        self._cen = integralfunc(x*yn,x)
        xp = x - self._cen
        
        
        if y[0] > 0.5 or y[-1] > 0.5:
            self._fwhm = (integralfunc(xp*xp*yn,xp)*8*np.log(2))**0.5 
        else:
            #from scipy.interpolation import interp1d
            #from scipy.optimize import newton
            #ier = interp1d(x,y-0.5)
            #lval-uval=newton(ier,x[0])-newton(ier,x[-1])
            #need peak to be 1 for this algorithm
            yo = y-0.5
            edgei = np.where(yo*np.roll(yo,1)<0)[0]-1
            li,ui = edgei[0]+np.arange(2),edgei[1]+np.arange(2)
            self._fwhm = np.interp(0,yo[ui],x[ui])-np.interp(0,yo[li],x[li])
            
    
    def _getNorm(self):
        return self._norm
    def _setNorm(self,val):
        val = bool(val)
        if val != self._norm:
            if self._norm:
                self.S *= self._N
            else:
                self.S /= self._N
        self._norm = val
    normalized = property(_getNorm,_setNorm)
        
    def _getCen(self):
        return self._cen
    
    def _getFWHM(self):
        return self._fwhm
    
    def _getx(self):
        if self.copyonaccess:
            return self._x.copy()
        else:
            return self._x
    
    def _getS(self):
        if self.copyonaccess:
            return self._S.copy()
        else:
            return self._S
        
        
class FileBand(ArrayBand):
    def __init__(self,fn,type=None):
        """
        type can be 'txt', or 'fits', or inferred from extension
        
        if txt, first column should be lambda, second should be response
        """
        from os import path
        
        self.fn = fn
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
        
        ArrayBand.__init__(self,x,S)
        
class CMDAnalyzer(object):
    """
    This class is intended to take multi-band photometry and compare it
    to fiducial models to find priorities/matches for a set of data from the
    same bands
    """
    
    @staticmethod
    def _dataAndBandsToDicts(bands,arr):
        from warnings import warn
        from operator import isSequenceType
        
        if len(bands) != arr.shape[0]:
            raise ValueError('fbands does not match fiducial bands')
        
        n = arr.shape[1]
        
        bandnames,bandobjs,colors=[],[],[]
        for b in bands:
            if type(b) is str:
                if '-' in b:
                    bandnames.append(None)
                    bandobjs.append(None)
                    colors.append(b)
                else:
                    bandnames.append(b)
                    bandobjs.append(bands[b])
                    colors.append(None)
            elif hasattr(b,'name'):
                bandnames.append(None)
                bandobjs.append(b)
                colors.append(None)
            else:
                raise ValueError("Can't understand input band "+str(b))
            
        bd={}
        datad={}
        maskd = {}
        for i,(n,b) in enumerate(zip(bandnames,bandobjs)):
            if b is not None:
                if n is None:
                    bd[b.name] = b
                    datad[b.name] = arr[i]
                else:
                    bd[n] = b
                    datad[n] = arr[i]
                    
        for i,c in enumerate(colors):
            b1,b2 = (b.strip() for b in c.split('-'))
            if b1 in bd and not b2 in bd:
                bd[b2] = bands[b2]
                datad[b2] = datad[b1] - arr[i]
                maskd[b2] = True
            elif b2 in bd and not b1 in bd:
                bd[b1] = bands[b1]
                datad[b1] = arr[i] - datad[b2]
                maskd[b1] = True
            elif b1 in bd and b2 in bd:
                warn('Bands %s and %s overedetermined due to color %s - using direct band measurements'%(b1,b2,c))
                #do nothing because bands are already defined
            else:
                warn('Bands %s and %s underdetermined with only color %s - assuming zeros for band %s'%(c,b1))
                bd[b1] = bands[b1]
                datad[b1] = np.zeros(n)
                maskd[b1] = False
                bd[b2] = bands[b2]
                datad[b2] = arr[i]
                maskd[b2] = True
                
        return bd,datad,maskd
    
    def __init__(self,fiducial,fbands,ferrs=None):
        """
        fiducial is a B x N array where B is the number of bands/colors
        and N is the number of fiducial points.  
        
        fbands specifies the band (either as a string or a Band object) or 
        color name (seperated by "-") matching the fiducial
        """
        from warnings import warn
        from operator import isSequenceType
        
        
        if ferrs is not None:
            raise NotImplementedError('errors not yet implemented')
        
        arr = np.atleast_2d(fiducial)
        bandd,datad,maskd = self._dataAndBandsToDicts(fbands,arr)
                
        self._banddict = bandd
        self._fdatadict = datad 
        self._bandnames = tuple(sorted(bandd.keys(),key=bandd.get))
        self._fidmask = np.array([maskd[b] for b in self._bandnames])
        self._nb = len(self._bandnames)
        self._nfid = arr.shape[1]
        
        self._data = None
        self._nd = 0
        
        self._offbands = None
        self._offsets  = None
        
        self._dmod = 0
        
    def _calculateOffsets(self):
        raise NotImplementedError
        #use self._offbands and self._dmod to set self._offsets
        if self._offbands is None:
            bands = [self._bandnames[i] for i,b in enumerate(self._fidmask & self._datamask) if b]
            fids = np.array([self._fdatadict[b]+self._dmod for b in bands],copy=False)
            dats = np.array([self._data[b] for b in bands],copy=False)
        else:
            fids,dats = [],[]
            for b in self._offbands:
                if isinstance(b,tuple):
                    fids.append(self._fdatadict[b[0]]-self._fdatadict[b[1]])
                    dats.append(self._data[b[0]]-self._data[b[1]])
                else:
                    fids.append(self._fdatadict[b]+self._dmod)
                    dats.append(self._data[b])
            fids,data = np.array(fids,copy=False),np.array(dats,copy=False)
            
        #TODO:interpolate along fiducials to a reasonable density
        #maybe need to transpose fids and data?  should be nfXnb and ndXnb
        datat = np.tile(data,(fids.shape[0],1,1)).transpose((1,0,2))
        diff = fids - data
        sep = np.sum(diff*diff,axis=2)**0.5
        self._offsets = np.min(sep,axis=1)
        
    def getBand(self,i):
        if isinstance(i,int):
            return self._banddict[self._bandnames[i]]
        elif isinstance(i,str):
            return self._banddict[i]
        raise TypeError('Band indecies must be band names or integers')
    
    def getFiducialData(self,i):
        if isinstance(i,int):
            return self._fdatadict[self._bandnames[i]]
        elif isinstance(i,str):
            return self._fdatadict[i]
        raise TypeError('Band indecies must be band names or integers')
    
    @property
    def bandnames(self):
        return self._bandnames
    
    def getData(self):
        return self._data
    def setData(self,val):
        """
        This loads the data to be compared to the fiducial sequence - the input
        can be an array (B X N) or an 
        """
        from operator import isMappingType
        if isMappingType(val):
            bandd,datad,maskd = self._dataAndBandsToDicts(val.keys(),np.atleast_2d(val.values()))
            
            arr = {}
            currnd = None
            for b,d in datad.iteritems():
                if b in self._bandnames:
                    bname = list(self._bandnames).index(b)
                    if maskd[bname]:
                        if currnd and len(d) != currnd:
                            raise ValueError('Band %s does not match previous band sizes'%b)
                        currnd = len(d)
                        arr[bname] = d
                        
            mask,dat = [],[]
            for delem in [arr.pop(i,None) for i in range(self._nb)]:
                if delem is None:
                    mask.append(False)
                    dat.append(np.NaN*np.empty(currnd))
                else:
                    mask.append(True)
                    dat.append(delem)
                    
            self._data = np.array(dat)
            self._datamask = np.array(mask)
            self._nd = currnd
            
        else:
            if len(val) != self._bandnames:
                raise ValueError('input sequence does not match number of bands')
            self._data = np.atleast_2d(val)
            self._nd = arr.shape[1]
            self._datamask
            
        #check to make sure the offset bands are ok for the new data
        try:
            self.offsetbands = self.offsetbands
        except ValueError:
            print 'new data incompatible with current offset bands - setting to use all'
            self._offbands = None
            
    def _getOffBands(self):
        if self._offbands is None:
            return None
        return ['%s-%s'%e if isinstance(e,tuple) else e for e in self._offbands]
    
    def _setOffBands(self,val):
        from operator import isSequenceType
        
        if val is None:
            self._offbands = None
        else:
            op = []
            lbn = list(self._bandnames)
            for i,v in enumerate(val):
                if isinstance(v,basestring):
                    vs = v.split('-')
                    if len(vs) == 2:
                        b1,b2 = vs
                        op.append((lbn.index(b1.strip()),lbn.index(b2.strip())))
                    else:
                        op.append(lbn.index(v.strip()))
                elif isinstance(v,int):
                    op.append(v)
                else:
                    try:
                        b1,b2 = v
                        if isinstance(b1,basestring):
                            op.append(lbn.index(b1))
                        else:
                            op.append(b1)
                        if isinstance(b2,basestring):
                            op.append(lbn.index(b2))
                        else:
                            op.append(b2)
                    except:
                        raise ValueError('uninterpretable band type in position '+i)
                    
            def docheck(v,i,j):
                #True indicates invalid, False is good
                if not isinstance(v,int):
                    raise TypeError('band index at position %i,%i is not an index'%(i,j))
                if v < 0:
                    raise IndexError('band index at position %i,%i is invalid'%(i,j))
                if v > self._nb:
                    raise IndexError('band index at position %i,%i is invalid'%(i,j))
                if not self._datamask[v]:
                    raise ValueError('data mask incompatible with band at position %i,%i'%(i,j))
                if not self._fidmask[v]:
                    raise ValueError('fiducial mask incompatible with band at position %i,%i'%(i,j))
            
            for i,v in enumerate(op):
                if isinstance(v,tuple):
                    #if ONE of the bands in a color is masked in the fiducial, it's still ok
                    fidok = True
                    try:
                        docheck(v[0],i,1)
                    except ValueError,e:
                        if 'fiducial' in e.message:
                            fidok = False
                        else:
                            raise e
                    try:
                        docheck(v[1],i,2)
                    except ValueError,e:
                        if 'fiducial' in e.message:
                            if not fidok:
                                raise e
                        else:
                            raise e
                docheck(v,0,0)
                    
            bandkeys = []
            for v in self._offbands:
                if isinstance(v,tuple):
                    bandkeys.append((self._bandnames[v[0]],self._bandnames[v[1]]))
                else:
                    bandkeys.append(self._bandnames[v])
    
            self._offbands = bandkeys
    offsetbands = property(_getOffBands,_setOffBands,doc="""
    this selects the bands or colors to use in determining offsets
    as a list of band names/indecies (or for colors, 'b1-b2' or a 2-tuple)
    if None, all the bands will be used directly.
    """)
        
    def getOffsets(self):
        """
        computes and returns the CMD offsets
        """
        if self._offsets is None:
            self._calculateOffsets()
        return self._offsets
    def clearOffsets(self):
        """
        clears the offsets for setting of properties without recalculation
        """
        self._offsets = None
    
    def _getDist(self):
        pass
    def _setDist(self,val):
        self._dist = val
        if self._offsets is not None:
            self._calculateOffsets()
        
    distance = property(_getDist,_setDist,doc="""
    The distance to use in calculating the offset between the fiducial values 
    and the data
    """)
    def _getDMod(self):
        return distance_from_modulus(self._dmod)
    def _setDMod(self,val):
        self._dmod = distance_modulus(val)
        if self._offsets is not None:
            self._calculateOffsets()
    distmod = property(_getDMod,_setDMod,doc="""
    The distance modulusto use in calculating the offset 
    between the fiducial values and the data 
    """)
        
        
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
        
    if isinstance(Mzpt,basestring):
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
        
    if isinstance(Mzpt,basestring):
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
        
    
        
    
#<---------------------Load built-in data-------------------------------------->
class _BandRegistry(dict):
    def __init__(self):
        dict.__init__(self)
        self._groupdict = {}
        
    def __getitem__(self,val):
        if val in self._groupdict:
            bands = self._groupdict[val]
            return dict([(b,self[b]) for b in bands])
        else:
            return dict.__getitem__(self,val)
    def __delitem__(self,key):
        dict.__delitem__(key)
        for k,v in self._groupdict.items():
            if key in v:
                del self.groupdict[k]
                
    def __getattr__(self,name):
        if name in self.keys():
            return self[name]
        else:
            raise AttributeError('No band or attribute '+name+' in '+self.__class__.__name__)
    
    def register(self,bands,groupname=None):
        """
        register a set of bands in a group
        
        bands is a dictionary mapping the band name to a Band object
        
        setname is the name of the group to apply to the dictionary
        """
        from operator import isMappingType,isSequenceType
        
        if not isMappingType(bands):
            raise ValueError('input must be a map of bands')
        for k,v in bands.iteritems():
            if not isinstance(v,Band):
                raise ValueError('an object in the band set is not a Band')
            self[str(k)]=v
            
        if groupname:
            if type(groupname) is str:
                self._groupdict[groupname] = bands.keys()
            elif isSequenceType(groupname):
                for s in groupname:
                    self._groupdict[s] = bands.keys()
            else:
                raise ValueError('unrecognized group name type')
            
    def groupnames(self):
        return self._groupdict.keys()
    
    def groupiteritems(self):
        for k in self.groupkeys():
            yield (k,self[k])

#TODO: check UBVRI/ugriz S function - energy or quantal?

def __load_UBVRI():
    from .io import _get_package_data
    bandlines = _get_package_data('UBVRIbands.dat').split('\n')
    
    src = bandlines.pop(0).replace('#Source:','').strip()
    bandlines.pop(0)
    
    d={}
    for ln in bandlines:
        if ln.strip() == '':
            pass
        elif 'Band' in ln:
            k = ln.replace('Band','').strip()
            xl = []
            Rl = []
            d[k]=(xl,Rl)
        else:
            t = ln.split()
            xl.append(t[0])
            Rl.append(t[1])
            
    d = dict([(k,ArrayBand(np.array(v[0],dtype='f8'),np.array(v[1],dtype='f8'),name=k)) for k,v in d.iteritems()])
    for v in d.itervalues():
        v.source = src
    return d

def __load_ugriz():
    from .io import _get_package_data
    bandlines = _get_package_data('ugrizbands.dat').split('\n')
    
    bandlines.pop(0)
    psrc = bandlines.pop(0).replace('#primes:','').strip()
    src = bandlines.pop(0).replace('#SDSS ugriz:','').strip()
    bandlines.pop(0)
    
    d={}
    for ln in bandlines:
        if ln.strip() == '':
            pass
        elif 'Band' in ln:
            k = ln.replace('Band','').strip()
            xl = []
            Rl = []
            d[k]=(xl,Rl)
        else:
            t = ln.split()
            xl.append(t[0])
            Rl.append(t[1])
            
    d = dict([(k,ArrayBand(np.array(v[0],dtype='f8'),np.array(v[1],dtype='f8'),name=k)) for k,v in d.iteritems()])
    for k,v in d.iteritems():
        if "'" in k:
            v.source = psrc
        else:
            v.source = src
    dp = {}
    for k in d.keys():
        if "'" in k: 
            dp[k]=d.pop(k)
    return d,dp

def __load_human_eye():
    from .io import _get_package_data
    bandlines = _get_package_data('eyeresponse.dat').split('\n')
    
    src = bandlines.pop(0).replace('#from','').strip()
    d={'cone_s':[],'cone_m':[],'cone_l':[]}
    for ln in bandlines:
        if ln.strip() == '':
            pass
        else:
            t = ln.strip().split(',')
            d['cone_l'].append((t[0],t[1]))
            d['cone_m'].append((t[0],t[2]))
            if t[3]!='':
                d['cone_s'].append((t[0],t[3]))
                
    
    d = dict([(k,np.array(v,dtype='f8')) for k,v in d.iteritems()])
    #logarithmic response data - must do 10**data, also, convert x-axis to angstroms
    d = dict([(k,ArrayBand(10*v[:,0],10**v[:,1],name=k)) for k,v in d.iteritems()])
    for v in d.itervalues():
        v.source = src
    return d


            
bands = _BandRegistry()
bands.register(__load_human_eye(),'eye')
d,dp = __load_ugriz()
bands.register(d,'ugriz')
bands.register(dp,'ugriz_prime')
del d,dp
bands.register(__load_UBVRI(),['UBVRI','UBVRcIc'])


class _BwlAdapter(dict): 
    def __getitem__(self,key):
        if key not in self:
            return bands[key].cen
        return dict.__getitem__(self,key)
bandwl = _BwlAdapter()
#photometric band centers - B&M ... deprecated, use bands[band].cen instead
bandwl.update({'U':3650,'B':4450,'V':5510,'R':6580,'I':8060,'u':3520,'g':4800,'r':6250,'i':7690,'z':9110})

del ABCMeta,abstractmethod,abstractproperty,HasSpecUnits #clean up namespace