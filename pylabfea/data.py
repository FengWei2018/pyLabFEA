#Module pylabfea.data
'''Module pylabfea.data introduces the class ``Data`` for handling of data resulting 
from virtual or physical mechanical tests in the pyLabFEA package. This class provides the 
methods necessary for analyzing data and for preparing it a training data for 
machine learning algorithms to be used a constitutive models.

uses NumPy, SciPy, MatPlotLib

Version: 2.1 (2020-04-01)
Author: Alexander Hartmaier, ICAMS/Ruhr-University Bochum, April 2020
Email: alexander.hartmaier@rub.de
distributed under GNU General Public License (GPLv3)'''

from pylabfea.basic import *
from pylabfea.model import Model
from pylabfea.material import Material
import numpy as np
import json
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib as mpl
import sys

'================='
'define data class'
'================='
class Data(object):
    '''Define class for handling data from virtual mechanical tests in micromechanical 
    simulations and data from physical mechanical tests on materials with various 
    microstructures
    
    Parameters
    ----------
    msl  : list
        List with names of JOSN files with metadata for all microstructures
    path_data : str
        Trunc of pathname for data files
    path_json : str
        Trunc of pathname for JSON metadata files (Optional, default: path_data)
    name : str
        Name of Dataset (optional, default: 'Dataset')
    nth  : int
        Read only every nth lines of input file (optional, default: 1)
    epl_crit : float
        Critical plastic strain at which yield strength is defined (optional, default: 2.e-3)
    d_ep     : float
        Range around critical value of plastic strain in which flow stresses are
        evaluated (optional, default: 5.e-4)
        
    Attributes
    ----------
    msl   : list
    Nset  : int
    name  : str
    pd    : str
    pj    : str
    epc   : float
    dep   : float
    set   : list
    sy_av : float
    E_av  : float
    nu_av : float
    texture : list
        List of all texture parameters of microstructures
    
    
    '''
    def __init__(self, msl, path_data, path_json=None, name='Dataset', nth=1, 
                            epl_crit=2.e-3, d_ep=5.e-4, plot=False):
        self.msl  = msl
        self.Nset = len(msl)
        self.name = name
        self.pd = path_data
        if path_json is not None:
            self.pj = path_json
        else:
            self.pj = self.pd
        self.nth = nth
        self.epc = epl_crit
        self.dep = d_ep
        self.set = []
        'import and pre-process data of all microstructure'
        for name in msl:
            self.set.append(self.Set(self, name, plot=plot))
        'calculate average properties over all microstructures'
        prop = np.zeros(3)
        micr = []
        for set in self.set:
            prop += np.array([set.sy, set.E, set.nu])
            micr.append(set.texture_param)
        prop /= self.Nset  # average properties over all microstructures
        self.sy_av = prop[0]
        self.E_av  = prop[1]
        self.nu_av = prop[2]
        self.texture = np.array(micr)
        
    class Set(object):
        '''Define class for handling of a dataset for one individual material 
    
        Parameters
        ----------
        db   : object of type ``Data``
            Parent database from which properties are inherited
        name : str
            Name of JSON file with metadata for microstructure to be stored in this dataset
        plot : Boolean
            Graphical output of data in each set (optional, default: False)
        
        Attributes
        ----------
        db : object of class ``Data``
        name : str
        N  : int
            Number of imported data points
        Ndat : int
            Number of raw data points (filtered data lying around yield point mirrored wrt polar angle)
        Nlc  : int
            Number of loadcase in raw data
        E, nu : float
            Elastic parameters obtained from data
        sy    : float
            Yield strength obtained from data
        texture_param : float
            Microstructure parameter for texture
        eps, epl, eel, sig, ubc : (N,) array
        sfc_   : (Ndat,) array
            Filtered cyl. stress tensor around yield point
        peeq_  : (Ndat,) array
            Filtered equiv. plastic strain around yield point
        ubc_   : (Ndat,) array
            Filtered boundary condition vector around yield point
        sig_   : (Ndat,) array
            Filtered princ. stress tensor around yield point
        f_yld_ : (Ndat,) array
            Categorial yield function of data points around yield point ("-1": elastic, "+1": plastic)
        i_el_  : (Ndat,) array
            Filtered indeces of data points lying in elastic regime
        i_pl_  : (Ndat,) array
            Filtered indeces for data points lying in plastic regime
        syc    : (Nlc,3) array
            Yield strength: interpolated cyl. stress tensor at onset of yielding for individual load cases
        load_case : list
            List of lists with data set indices belonging to one single load case (index space: [0,N])
        lc_    : list
            List of lists with data set indices belonging to one single load case (index space: [0,Ndat])
    
        '''
        def __init__(self, db, name, plot=False):
            '''def prop_elastic():
                'calculate estimates for elastic properties E, nu associated to data set'
                ssig = 1.e-1
                seps = 1.e3
                a = seps*self.eps[ind,:]
                b = ssig*self.sig[ind,:]
                x = np.linalg.lstsq(a, b, rcond=None)
                c = x[0]*seps/ssig
                self.C11 = c[0,0]
                self.C12 = c[1,0]
                self.C13 = c[2,0]
                self.C21 = c[0,1]
                self.C22 = c[1,1]
                self.C23 = c[2,1]
                self.C31 = c[0,2]
                self.C32 = c[1,2]
                self.C33 = c[2,2]
                
                #self.nu = self.C12/(self.C11 + self.C12) # estimate for isotropic materials
                #self.E = self.C12*(1.+self.nu)*(1.-2.*self.nu)/self.nu
                
                print('Estimated elasic tensor C_ij (GPa): \n%8.2f, %8.2f, %8.2f' 
                       % (self.C11/1000, self.C12/1000, self.C13/1000))
                print('%8.2f, %8.2f, %8.2f' 
                       % (self.C21/1000, self.C22/1000, self.C23/1000))
                print('%8.2f, %8.2f, %8.2f' 
                       % (self.C31/1000, self.C32/1000, self.C33/1000))
                print('Residuals of fitting elastic parameters: ',x[1])'''
            
            self.name = name
            self.db = db
            with open(db.pj+name+'.json') as f:
                self.meta = json.load(f)

            'import data from CSV files of micromechanical simulations'
            sep   = self.meta['CSV_separator']
            file  = db.pd + self.meta['CSV_data']
            names = self.meta['CSV_format'].split(sep)
            AllData = pd.read_csv(file,header=1,names=names,sep=sep)
            sig_names = ['S11','S22','S33']
            epl_names = ['Ep11','Ep22','Ep33']
            eps_names = ['E11','E22','E33']
            eel_names = ['Ee11','Ee22','Ee33']
            ubc_names = ['StrainX', 'StrainY', 'StrainZ']
            self.eps = AllData[eps_names].to_numpy()[::db.nth]
            self.epl = AllData[epl_names].to_numpy()[::db.nth]
            self.eel = AllData[eel_names].to_numpy()[::db.nth]
            self.sig = AllData[sig_names].to_numpy()[::db.nth]
            self.ubc = AllData[ubc_names].to_numpy()[::db.nth]
            self.N = np.shape(self.sig)[0]
            print('\n*** Microstructure:',self.name,'***')
            print(self.N,' data points imported into database ',self.db.name)
            
            '''
            'import Fourier coefficients'
            fc_name = db.pd + self.meta['Fourier_coeff']
            f = open(fc_name, 'r')
            for x in f:
                print(x[0], x)
            '''
            self.texture_param = int(self.name[-1])
            
            'calculate eqiv. stresses and strains and theta values'
            sc_full   = s_cyl(self.sig)   # transform stresses into cylindrical coordinates
            peeq_full = eps_eq(self.epl)  # calculate equiv. plastic strain from data
            
            'Consistency checks'
            if np.amax(np.abs(sc_full[:,2])) > 1.:
                print('*** Warning: Large hydrostatic stresses: minimum p=%5.2f MPa, maximum p=%5.2f MPa' 
                      %(np.amin(sc_full[:,2]),np.amax(sc_full[:,2])))
            '''hh = self.eel - (self.eps-self.epl)
            if np.amax(eps_eq(hh)) > 1.e-8:
                print('*** WARNING: Inconsistency in eps_el!')
            hh = self.ang - sc_full[:,1]
            if np.amax(np.abs(hh)) > 1.e-6:
                print('*** WARNING: Inconsistency in theta!')
                print(self.ang[0:self.N:2500], sc_full[0:self.N:2500,1], hh[0:self.N:2500])'''

            'filter load cases'
            self.load_case = []   # list of lists with data set indices belonging to one load case
            hh = []
            uvec = self.ubc[0,:]
            for i in range(self.N):
                if np.linalg.norm(self.ubc[i,:]-uvec) < 1.e-6:
                    hh.append(i)
                else:
                    self.load_case.append(hh)
                    hh = []
                    uvec = self.ubc[i,:]
            
            'select data points close to yield point => yield strength sy and raw data for ML flow rule'
            ind = np.nonzero(np.logical_and(peeq_full>db.epc-db.dep, peeq_full<db.epc+db.dep))[0]
            scyl_raw = sc_full[ind]
            peeq_raw = peeq_full[ind]
            self.Ndat = len(ind)
            self.sy = np.average(scyl_raw[:,0])  # get first estimate of yield point, will be refined later
            
            'mirror stress data w.r.t. theta in deviatoric stress space'
            sc2 = np.zeros((self.Ndat,2))
            sc2[:,0] = scyl_raw[:,0]
            sc2[:,1] = scyl_raw[:,1]-np.pi
            ih = np.nonzero(sc2[:,1]<-np.pi)[0]
            sc2[ih,1] += 2*np.pi
            
            'calculate associated load vector for boundary conditions'
            hs1 = self.sig[ind,:]     # original stresses
            hs2 = sp_cart(sc2)        # mirrored stresses
            sign = np.sign(hs1*hs2)   # filter stress components where sign has changed by mirroring
            ubc2 = self.ubc[ind]*sign # change sign accordingly in BC vector

            'add mirrored data to flow stresses and augment plastic strain arrays accordingly'
            self.sfc_  = np.append(scyl_raw[:,0:2], sc2, axis=0) 
            self.peeq_ = np.append(peeq_raw, peeq_raw, axis=0)
            self.ubc_  = np.append(self.ubc[ind], ubc2, axis=0)
            self.sig_  = sp_cart(self.sfc_) # transform back into 3D principle stress space
            self.Ndat *= 2    # number of load cases in raw data
            
            'calculate yield function of raw data'
            self.f_yld_ = np.sign(self.peeq_ - db.epc)
            self.i_el_  = np.nonzero(self.f_yld_<0.)[0]
            self.i_pl_  = np.nonzero(self.f_yld_>=0.)[0]
            
            'filter load cases of raw data'
            self.lc_ = []   # list of lists with data set indices belonging to one load case
            hh = []
            uvec = self.ubc_[0,:]
            for i in range(self.Ndat):
                if np.linalg.norm(self.ubc_[i,:]-uvec) < 1.e-6:
                    hh.append(i)
                else:
                    self.lc_.append(hh)
                    hh = []
                    uvec = self.ubc_[i,:]
            self.Nlc = len(self.lc_)
            print('Number of load cases: ',self.Nlc)

            'calculate yield stress for each load case'
            hs = []
            ht = []
            for i in range(self.Nlc):
                ind = self.lc_[i]
                iel = np.nonzero(self.f_yld_[ind]<0.)[0]  # find elastic data sets in load case
                ipl = np.nonzero(self.f_yld_[ind]>=0.)[0] # find plastic data sets in load case
                ds = self.sfc_[ind[ipl[0]],0] - self.sfc_[ind[iel[-1]],0]   # difference in seq b/w first plastic and last elastic data point
                de = self.peeq_[ind[ipl[0]]]  - self.peeq_[ind[iel[-1]]]    # difference in peeq b/w first plastic and last elastic data point
                hs.append(self.sfc_[ind[iel[-1]],0] + (db.epc-self.peeq_[ind[iel[-1]]])*ds/de) # linearly interpolated equiv. stress at yield onset
                ht.append(self.sfc_[ind[iel[-1]],1]) # polar angle of load case
            ind = np.argsort(ht)   # sort w.r.t. polar angle
            self.syc = np.zeros((self.Nlc,3))   # critical cylindrical stress tensor at yield onset
            self.syc[:,0] = np.array(hs)[ind]   # first component: seq
            self.syc[:,1] = np.array(ht)[ind]   # second component: polar angle
            self.sy = np.average(self.syc[:,0]) # refined value for yield strength of data set
            
            'select data points with eqiv. stress in range [0.1,0.4]sy => elastic constants'
            seq = seq_J2(self.sig)
            ind1 = np.nonzero(np.logical_and(seq>0.1*self.sy, seq<0.4*self.sy))[0]
            seq = seq_J2(self.sig[ind1])
            eeq = eps_eq(self.eps[ind1])
            self.E = np.average(seq/eeq)
            self.nu = 0.3
            
            print('Estimated elasic constants: E=%5.2f GPa, nu=%4.2f' % (self.E/1000, self.nu))
            print('Estimated yield strength: %5.2f MPa, from %i data sets with PEEQ approx. %5.3f' 
                  %(self.sy,self.Ndat,db.epc))
            if plot:
                self.plot_set()
                   
        def augment_data(self, plot=False):
            '''Raw data is distributed over entire deviatoric plane to create a suited
            data set for training of SVC, graphical output of raw data together with 
            augmented data can be created.
            '''
            
            'augment raw data and create result vector (yield function)'
            self.sc_train, self.yf_train = mat.create_sig_data(syc=self.syc, Nseq=25, extend=True)
            self.sc_test, self.yf_test   = mat.create_sig_data(syc=self.syc[::12,:], Nseq=15)

            if plot:
                print('Plot raw data and training data extended over deviatoric plane for data set ',self.name)
                fig, ax  = plt.subplots(nrows=1, ncols=1, figsize=(10,8))
                Ncol = int(len(self.sc_train)/self.Nlc)
                ax.scatter(self.sc_train[:,1], self.sc_train[:,0], s=15, c=self.yf_train, cmap=plt.cm.Paired)
                #ax.plot(self.sfc_[:,1], self.sfc_[:,0], '.y')
                ax.plot(self.syc[:,1], self.syc[:,0], '-k')
                ax.set_title('SVC yield function for data set '+self.name)
                ax.set_xlabel(r'$\theta$ (rad)', fontsize=20)
                ax.set_ylabel(r'$\sigma_{eq}$ (MPa)', fontsize=20)
                ax.tick_params(axis="x", labelsize=16)
                ax.tick_params(axis="y", labelsize=16)
                plt.show()

        def plot_set(self, file=None, nth=18, fontsize=18):
            '''Graphical output of equiv. stress vs. equic. total strain for selected load cases and 
            raw data in deviatoric cyl. stress space
            
            Parameters
            ----------
            file : str
                Write graph to pdf file (optional)
            nth  : int
                Plot every nth load case (optional, default: 18)
            fontsize : 20
                Fontsize for plot (optional, default: 20)
            '''
            fig = plt.figure(figsize=(16,7))
            plt.subplots_adjust(wspace=0.6)
            N = len(self.load_case)
            ax = plt.subplot(1,2,1)
            for i in range(0,N,nth):
                ind = self.load_case[i]
                plt.plot(eps_eq(self.eps[ind])*100, seq_J2(self.sig[ind]), '.k')
            plt.xlabel(r'$\epsilon_{eq}^\mathrm{tot}$ (%)', fontsize=fontsize)
            plt.ylabel(r'$\sigma_{eq}$ (MPa)', fontsize=fontsize)
            plt.title('Equiv. total strain vs. equiv. J2 stress', fontsize=fontsize)
            plt.tick_params(axis="x", labelsize=fontsize-4)
            plt.tick_params(axis="y", labelsize=fontsize-4)
            
            ax = plt.subplot(1, 2, 2) #, projection='polar')
            plt.plot(self.sfc_[self.i_pl_,1], self.sfc_[self.i_pl_,0], 'or')
            plt.plot(self.sfc_[self.i_el_,1], self.sfc_[self.i_el_,0], 'ob')
            plt.plot(self.syc[:,1], self.syc[:,0], '-k')
            plt.plot([-np.pi, np.pi], [self.sy, self.sy], '--k')
            plt.legend(['raw data above yield point', 'raw data below yield point', 
                           'interpolated yield strength', 'average yield strength'],loc=(1.04,0.7),fontsize=fontsize-2)
            plt.title('Raw data '+self.name, fontsize=fontsize)
            plt.xlabel(r'$\theta$ (rad)', fontsize=fontsize)
            plt.ylabel(r'$\sigma_{eq}$ (MPa)', fontsize=fontsize)
            plt.tick_params(axis="x", labelsize=fontsize-4)
            plt.tick_params(axis="y", labelsize=fontsize-4)
            if file is not None:
                plt.savefig(file+self.name+'.pdf', format='pdf', dpi=300)
            plt.show()
            

    
    def plot_yield_locus(self, file=None, fontsize=18):
        '''Plot yield loci of imported microstructures in database.
        '''
        fig = plt.figure(figsize=(15, 8))
        cmap = mpl.cm.get_cmap('plasma', 10)
        legend = []
        tp_max = 0.
        for set in self.set:
            tp_max = np.maximum(tp_max, set.texture_param)
            
        for set in self.set:
            plt.polar(set.syc[:,1], set.syc[:,0], color=cmap(set.texture_param/tp_max-0.25))
            legend.append(set.name)
            plt.legend(legend,loc=(1.04,0.7),fontsize=fontsize-2)
        if file is not None:
            plt.savefig(file+'.pdf', format='pdf', dpi=300)
        plt.tick_params(axis="x", labelsize=fontsize-4)
        plt.tick_params(axis="y", labelsize=fontsize-4)
        plt.show()
