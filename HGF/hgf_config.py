""" Fuctions for model fitting and model simulation of the Hierarchical Gaussian Filter
code takes in stimulus states and simulates perception and prediction of an agent

Model implemented as discribed in: Mathys, C. D., Lomakina, E. I., Daunizeau, J., Iglesias, S., Brodersen, K. H., Friston, K. J., & Stephan, K. E. (2014). Uncertainty in perception and the Hierarchical Gaussian Filter. Frontiers in human neuroscience, 8, 825.

Code adapted by Jorie van Haren (2021) """

# load nessecary packages
import numpy as np
import sys
import statsmodels.api as sm
from scipy import optimize

###################
# CONFIGURATIONS ##
###################

# perceptual models


def softmax_mu3_config():    
    
    c = {}
    c['predorpost'] = 1
    c['model'] = 'softmax_mu3'

    c['priormus'] = np.array([])
    c['priorsas'] = np.array([])
    c['prc_fun'] = 'softmax_mu3'
    c['transp_prc_fun'] = 'softmax_mu3_transp'
    return c

def hgf_ar1_binary_mab_config(): 

    c = {}
    # Model name
    c.model = 'hgf_ar1_binary_mab'
    # Number of levels (minimum: 3)
    c.n_levels = 3
    # Number of bandits
    c.n_bandits = 3
    # Coupling
    # This may only be set to true if c.n_bandits is set to 2 above. If
    # true, it means that the two bandits' winning probabilities are
    # coupled in the sense that they add to 1 and are both updated on
    # each trial even though only the outcome for one of them is observed.
    c.coupled = False
    # Input intervals
    # If input intervals are irregular, the last column of the input
    # matrix u has to contain the interval between inputs k-1 and k
    # in the k-th row, and this flag has to be set to true
    c.irregular_intervals = False
    # Sufficient statistics of Gaussian parameter priors
    
    # Initial mus and sigmas
    # Format: row vectors of length n_levels
    # For all but the first two levels, this is usually best
    # kept fixed to 1 (determines origin on x_i-scale). The
    # first level is NaN because it is determined by the second,
    # and the second implies neutrality between outcomes when it
    # is centered at 0.
    c.mu_0mu = np.array([np.NaN,0,1])
    c.mu_0sa = np.array([np.NaN,1,1])
    c.logsa_0mu = np.array([np.NaN,np.log(0.1),np.log(1)])
    c.logsa_0sa = np.array([np.NaN,1,1])
    # Phis
    # Format: row vector of length n_levels.
    # Undefined (therefore NaN) at the first level.
    # Fix this to zero (-Inf in logit space) to set to zero.
    c.logitphimu = np.array([np.NaN,tapas_logit(0.4,1),tapas_logit(0.2,1)])
    c.logitphisa = np.array([np.NaN,1,1])
    # ms
    # Format: row vector of length n_levels.
    # This should be fixed for all levels where the omega of
    # the next lowest level is not fixed because that offers
    # an alternative parametrization of the same model.
    c.mmu = np.array([np.NaN,c.mu_0mu(2),c.mu_0mu(3)])
    c.msa = np.array([np.NaN,0,0])
    # Kappas
    # Format: row vector of length n_levels-1.
    # Fixing log(kappa1) to log(1) leads to the original HGF model.
    # Higher log(kappas) should be fixed (preferably to log(1)) if the
    # observation model does not use mu_i+1 (kappa then determines the
    # scaling of x_i+1).
    c.logkamu = np.array([np.log(1),np.log(0.6)])
    c.logkasa = np.array([0,0.1])
    # Omegas
    # Format: row vector of length n_levels.
    # Undefined (therefore NaN) at the first level.
    c.ommu = np.array([np.NaN,- 2,- 2])
    c.omsa = np.array([np.NaN,1,1])
    # Gather prior settings in vectors
    c.priormus = np.array([c.mu_0mu,c.logsa_0mu,c.logitphimu,c.mmu,c.logkamu,c.ommu])
    c.priorsas = np.array([c.mu_0sa,c.logsa_0sa,c.logitphisa,c.msa,c.logkasa,c.omsa])
    # Check whether we have the right number of priors
    expectedLength = 5 * c.n_levels + (c.n_levels - 1)
    if len(np.array([c.priormus,c.priorsas])) != 2 * expectedLength:
        raise Exception('tapas:hgf:PriorDefNotMatchingLevels','Prior definition does not match number of levels.')
    
    # Model function handle
    c.prc_fun = 'hgf_ar1_binary_mab'
    # Handle to function that transforms perceptual parameters to their native space
    # from the space they are estimated in
    c.transp_prc_fun = 'hgf_ar1_binary_mab_transp'
    return c

def hgf_binary_config():
    """contains config for the Hierarchical Gaussian Filter (HGF)
    for binary inputs in the absence of perceptual uncertainty"""
    
    # initiate a config data dict
    c = {}
    
    ##########################################
    ## START GENERAL CONFIGURABLE VARIABLES ##
    ##########################################
    
    c['model']      = 'hgf_binary'       # model name
    c['n_levels']   = 3                  # number of levels (min 3)
    c['irregular_intervals'] = False     # input intervals, if input intervals are irregual must be set to True
    
    # initial mus and sigmas (of length n_levels)
    # set for all except first two levels
    # first level is always set to NaN as it is determined by the second
    # second level implies neutrality between outcomes when centered at 0
    c['mu_0mu'] = np.array([np.nan, 0, 1])
    c['mu_0sa'] = np.array([np.nan, 0, 0])
    c['logsa_0mu'] = np.array([np.nan, np.log(0.1), np.log(1)])
    c['logsa_0sa'] = np.array([np.nan, 0, 0])
    
    # set Rhos (of length n_levels)
    # undefined first level
    # fix to zero to turn off drift
    c['rhomu'] = np.array([np.nan, 0, 0])
    c['rhosa'] = np.array([np.nan, 0, 0])
    
    # set Kappas (of length n_levels-1)
    # higher log(kapps) should be fixed if observation model does not use mu_i+1
    # kappa then determines the scaling of x_i+1
    c['logkamu'] = np.array([np.log(1), np.log(1)])
    c['logkasa'] = np.array([0, 0])
    
    # set Omegas (of length n_levels)
    # undificed first level
    c['ommu'] = np.array([np.nan, -3, -6])
    c['omsa'] = np.array([np.nan, 4**2, 4**2])
    
    ########################################
    
    # gather prior settings in vectors
    c['priormus'] = np.concatenate([c['mu_0mu'], c['logsa_0mu'], c['rhomu'], c['logkamu'], c['ommu']], axis=0)
    c['priorsas'] = np.concatenate([c['mu_0sa'], c['logsa_0sa'], c['rhosa'], c['logkasa'], c['omsa']], axis=0)
    
    #  quicly check whether we have the right number of priors
    expectedlength = (3 * c['n_levels']) + (2 * (c['n_levels']-1)) + 1
    if len(c['priormus']) + len(c['priorsas']) != 2* expectedlength:
        raise Exception('hgf - Prior definition does not match number of levels.')
    
    c['prc_fun'] = 'hgf_binary'          # model function name
    c['transp_prc_fun'] = 'hgf_transp'   # function name to transform percp. para > native space
    return(c)


def hgf_config():
    """contains config for the Hierarchical Gaussian Filter (HGF)
    for continuus inputs in the absence of perceptual uncertainty"""
    
    # initiate a config data dict
    c = {}
    
    ##########################################
    ## START GENERAL CONFIGURABLE VARIABLES ##
    ##########################################
    
    c['model']      = 'hgf'       # model name
    c['n_levels']   = 2                  # number of levels (min 2)
    c['irregular_intervals'] = False     # input intervals, if input intervals are irregual must be set to True
    
    # initial mus and sigmas (of length n_levels)
    # set for all except first level
    # 9999x values get replaced later
    c['mu_0mu'] = np.array([99991, 1])
    c['mu_0sa'] = np.array([99992, 0])
    c['logsa_0mu'] = np.array([99993, np.log(0.1)])
    c['logsa_0sa'] = np.array([1, 1])
    
    # set Rhos (of length n_levels)
    # fix to zero to turn off drift
    c['rhomu'] = np.array([0, 0])
    c['rhosa'] = np.array([0, 0])
    
    # set Kappas (of length n_levels-1)
    # higher log(kapps) should be fixed if observation model does not use mu_i+1
    # kappa then determines the scaling of x_i+1
    c['logkamu'] = np.array([np.log(1)])
    c['logkasa'] = np.array([0])
    
    # set Omegas (of length n_levels)
    c['ommu'] = np.array([99993, -4])
    c['omsa'] = np.array([4**2, 4**2])
    
    # pi_u, set to zero for no perceptual uncertainty
    c['logpiumu'] = np.array([-99993])
    c['logpiusa'] = np.array([2**2])
    
    ########################################
    
    # gather prior settings in vectors
    c['priormus'] = np.concatenate([c['mu_0mu'], c['logsa_0mu'], c['rhomu'], c['logkamu'], c['ommu'], c['logpiumu']], axis=0)
    c['priorsas'] = np.concatenate([c['mu_0sa'], c['logsa_0sa'], c['rhosa'], c['logkasa'], c['omsa'], c['logpiusa']], axis=0)
    
    #  quicly check whether we have the right number of priors
    expectedlength = (3 * c['n_levels']) + (2 * (c['n_levels']-1)) + 2
    if len(c['priormus']) + len(c['priorsas']) != 2* expectedlength:
        raise Exception('hgf - Prior definition does not match number of levels.')

    c['prc_fun'] = 'hgf'                 # model function name
    c['transp_prc_fun'] = 'hgf_transp'   # function name to transform percp. para > native space
    return(c)


def ehgf_config():
    """contains config for the enhanced Hierarchical Gaussian Filter (HGF)
    for continuus inputs in the absence of perceptual uncertainty"""
    
    # initiate a config data dict
    c = {}
    
    ##########################################
    ## START GENERAL CONFIGURABLE VARIABLES ##
    ##########################################
    
    c['model']      = 'ehgf'             # model name
    c['n_levels']   = 2                  # number of levels (min 2)
    c['irregular_intervals'] = False     # input intervals, if input intervals are irregual must be set to True
    
    # initial mus and sigmas (of length n_levels)
    # set for all except first level
    c['mu_0mu'] = np.array([99991, 1])
    c['mu_0sa'] = np.array([99992, 0])
    c['logsa_0mu'] = np.array([99993, np.log(0.1)])
    c['logsa_0sa'] = np.array([1, 1])
    
    # set Rhos (of length n_levels)
    # fix to zero to turn off drift
    c['rhomu'] = np.array([0, 0])
    c['rhosa'] = np.array([0, 0])
    
    # set Kappas (of length n_levels-1)
    # higher log(kapps) should be fixed if observation model does not use mu_i+1
    # kappa then determines the scaling of x_i+1
    c['logkamu'] = np.array([np.log(1)])
    c['logkasa'] = np.array([0])
    
    # set Omegas (of length n_levels)
    c['ommu'] = np.array([99993, -4])
    c['omsa'] = np.array([4**2, 4**2])
    
    # pi_u, set to zero for no perceptual uncertainty
    c['logpiumu'] = np.array([-99993])
    c['logpiusa'] = np.array([2**2])
    
    ########################################
    
    # gather prior settings in vectors
    c['priormus'] = np.concatenate([c['mu_0mu'], c['logsa_0mu'], c['rhomu'], c['logkamu'], c['ommu'], c['logpiumu']], axis=0)
    c['priorsas'] = np.concatenate([c['mu_0sa'], c['logsa_0sa'], c['rhosa'], c['logkasa'], c['omsa'], c['logpiusa']], axis=0)
    
    #  quicly check whether we have the right number of priors
    expectedlength = (3 * c['n_levels']) + (2 * (c['n_levels']-1)) + 2
    if len(c['priormus']) + len(c['priorsas']) != 2* expectedlength:
        raise Exception('hgf - Prior definition does not match number of levels.')

    c['prc_fun'] = 'hgf'                 # model function name
    c['transp_prc_fun'] = 'hgf_transp'   # function name to transform percp. para > native space
    return(c)


def ehgf_binary_config():
    """contains config for the enhanced Hierarchical Gaussian Filter (eHGF)
    for binary inputs in the absence of perceptual uncertainty"""
    
    # initiate a config data dict
    c = {}
    
    ##########################################
    ## START GENERAL CONFIGURABLE VARIABLES ##
    ##########################################
    
    c['model']      = 'ehgf_binary'      # model name
    c['n_levels']   = 3                  # number of levels (min 3)
    c['irregular_intervals'] = False     # input intervals, if input intervals are irregual must be set to True
    
    # initial mus and sigmas (of length n_levels)
    # set for all except first two levels
    # first level is always set to NaN as it is determined by the second
    # second level implies neutrality between outcomes when centered at 0
    c['mu_0mu'] = np.array([np.nan, 0, 1])
    c['mu_0sa'] = np.array([np.nan, 0, 0])
    c['logsa_0mu'] = np.array([np.nan, np.log(0.1), np.log(1)])
    c['logsa_0sa'] = np.array([np.nan, 0, 0])
    
    # set Rhos (of length n_levels)
    # undefined first level
    # fix to zero to turn off drift
    c['rhomu'] = np.array([np.nan, 0, 0])
    c['rhosa'] = np.array([np.nan, 0, 0])
    
    # set Kappas (of length n_levels-1)
    # fixing log(kappa1) to log(1) is identical to normal HGF model
    # higher log(kapps) should be fixed if observation model does not use mu_i+1
    # kappa then determines the scaling of x_i+1
    c['logkamu'] = np.array([np.log(1), np.log(1)])
    c['logkasa'] = np.array([0, 0])
    
    # set Omegas (of length n_levels)
    # undificed first level
    c['ommu'] = np.array([np.nan, -3, 2])
    c['omsa'] = np.array([np.nan, 4, 4])
    
    ########################################
    
    # gather prior settings in vectors
    c['priormus'] = np.concatenate([c['mu_0mu'], c['logsa_0mu'], c['rhomu'], c['logkamu'], c['ommu']], axis=0)
    c['priorsas'] = np.concatenate([c['mu_0sa'], c['logsa_0sa'], c['rhosa'], c['logkasa'], c['omsa']], axis=0)
    
    #  quicly check whether we have the right number of priors
    expectedlength = (3 * c['n_levels']) + (2 * (c['n_levels']-1)) + 1
    if len(c['priormus']) + len(c['priorsas']) != 2* expectedlength:
        raise Exception('hgf - Prior definition does not match number of levels.')
    
    c['prc_fun'] = 'hgf_binary'          # model function name
    c['transp_prc_fun'] = 'hgf_transp'   # function name to transform percp. para > native space
    
    return(c)



# observational models

def unitsq_sgm_config():
    """contains the config for the unit square sigmoid 
    observation model for binary responses"""
    
    # initiate a config data dict
    c = {}
    
    ##########################################
    ## START GENERAL CONFIGURABLE VARIABLES ##
    ##########################################
    
    # decision based on predictions (1), or posteriors (2)
    c['predorpost'] = 1
    c['model'] = 'unitsq_sgm'
    
    # set Zeta
    c['logzemu'] = np.log(48)
    c['logzesa'] = 1
    
    ##########################################
    
    # gather prior settings in vector
    c['priormus'] = np.array([c['logzemu']])
    c['priorsas'] = np.array([c['logzesa']])
    
    c['obs_fun'] = 'unitsq_sgm'                 # model function name
    c['transp_obs_fun'] = 'unitsq_sqm_transp'   # function name to transform obs. para > native space
    return(c)


def gaussian_obs_config():
    """contains the config for the unit square sigmoid 
    observation model for binary responses"""
    
    # initiate a config data dict
    c = {}
    
    ##########################################
    ## START GENERAL CONFIGURABLE VARIABLES ##
    ##########################################
    
    # decision based on predictions (1), or posteriors (2)
    c['predorpost'] = 1
    c['model'] = 'gaussian_obs'
    
    # set Zeta
    c['logzemu'] = np.log(0.005)
    c['logzesa'] = 0.1
    
    ##########################################
    
    # gather prior settings in vector
    c['priormus'] = np.array([c['logzemu']])
    c['priorsas'] = np.array([c['logzesa']])
    
    c['obs_fun'] = 'gaussian_obs'                 # model function name
    c['transp_obs_fun'] = 'unitsq_sqm_transp'   # function name to transform obs. para > native space
    return(c)


def bayes_optimal_binary_config():
    """contains the config for the estimation of 
    bayes optimal perceptual parameters"""
    
    # initiate a config data dict
    c = {}
    
    ##########################################
    ## START GENERAL CONFIGURABLE VARIABLES ##
    ##########################################
    
    # model name
    c['model'] = 'Bayes optimal (binary)'
    
    # gather prior settings in vector
    c['priormus'] = np.array([])
    c['priorsas'] = np.array([])
    
    # model name
    c['obs_fun'] = 'bayes_optimal_binary'
    c['transp_obs_fun'] = 'bayes_optimal_binary'
    return(c)


def bayes_optimal_config():
    """contains the config for the estimation of 
    bayes optimal perceptual parameters"""
    
    # initiate a config data dict
    c = {}
    
    #TODO: Bayes model has not included this line, but we need it for softmax_mu3
    # Lets set it to 0?
    c['predorpost'] = 0
    
    ##########################################
    ## START GENERAL CONFIGURABLE VARIABLES ##
    ##########################################
    
    # model name
    c['model'] = 'Bayes optimal'
    
    # gather prior settings in vector
    c['priormus'] = np.array([])
    c['priorsas'] = np.array([])
    
    # model name
    c['obs_fun'] = 'bayes_optimal'
    c['transp_obs_fun'] = 'bayes_optimal'
    return(c)



# optimization model

def quasinewton_optim_config():
    """contains the config for the Broyden, Fletcher, 
    Goldfarb and Shanno (BFGS) quasi-Newton optimization algorithm"""
    
    # initiate a config data dict
    c = {}
    
    ##########################################
    ## START GENERAL CONFIGURABLE VARIABLES ##
    ##########################################
    
    c['algorithm'] = 'BFGS quasi-Newton'
    c['verbose']   = False  # verbosity
    c['tolGrad']   = 1e-3   # optimization option: 
    c['tolArg']    = 1e-3   # optimization option: 
    c['maxStep']   = 2      # optimization option: maximum stepsize
    c['maxIter']   = 1e3    # optimization option: maximum number of itterations 
    c['maxRegu']   = 4     # optimization option: maximum regu
    c['maxRst']    = 4     # optimization option: 
    c['nRandInit'] = 0
    
    ##########################################
    
    c['opt_fun'] = 'optimize.minimize'
    c['opt_method'] = 'BFGS'
    
    return(c)
    
