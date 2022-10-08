""" Fuctions for model fitting and model simulation of the Hierarchical Gaussian Filter
code takes in stimulus states and simulates perception and prediction of an agent

Model implemented as discribed in: Mathys, C. D., Lomakina, E. I., Daunizeau, J., Iglesias, S., Brodersen, K. H., Friston, K. J., & Stephan, K. E. (2014). Uncertainty in perception and the Hierarchical Gaussian Filter. Frontiers in human neuroscience, 8, 825.

Code adapted by Jorie van Haren (2021) """

# load nessecary packages
import numpy as np
from numpy import matlib
import statsmodels.api as sm
import pandas as pd
from scipy import optimize

# load config files
from HGF.hgf_config import *

####################
## MAIN FUNCTIONS ##
####################

def softmax_mu3(r=None, infStates=None, trans=None):

    pop = 0

    if r['c_obs']['predorpost'] == 1:
        pop = 2

    n = infStates.shape[0]
    logp = np.full([n, 1], np.nan)
    yhat = np.full([n, 1], np.nan)
    res = np.full([n, 1], np.nan)

    #TODO: This index is out of bounds; why?
    nc = infStates.shape[2]
    states = np.squeeze(infStates[:, 0, :, pop])
    mu3 = np.squeeze(infStates[:, 2, 0, 2])
    y = r['y'][:, 0]
    # TODO
    # states[r['irr'], :] = []
    # mu3 = np.delete(mu3, obj=:, r['irr'])
    y = np.delete(y, r['irr'])
    be = np.exp(- mu3)
    be = np.matlib.repmat(be, 1, nc)
    # TODO
    # Operands could not be broadcast together with shapes (n,nc) (n,1)
    Z = np.sum(np.exp(np.multiply(be, states)), 1)
    Z = np.matlib.repmat(Z, 1, nc)
    prob = np.exp(np.multiply(be, states)) / Z
    probc = prob(sub2ind(prob.shape, np.arange(1, len(y)+1), np.transpose(y)))
    reg = not ismember(np.arange(1, n+1), r['irr'])
    logp[reg] = np.log(probc)
    yhat[reg] = probc
    res[reg] = - np.log(probc)
    return logp, yhat, res

def hgf_ar1_binary_mab(r = None,p = None,varargin = None): 
    # Transform paramaters back to their native space if needed
    if not len(varargin)==0  and str(varargin[0]) == str('trans'):
        p = hgf_ar1_binary_mab_transp(r,p)
    
    # Number of levels
    l = r.c_prc.n_levels
    b = r.c_prc.n_bandits
    
    # Coupled updating
    # This is only allowed if there are 2 bandits. We here assume that the mu1hat for the two bandits
    # add to unity.
    coupled = False
    if r.c_prc.coupled == True:
        if b == 2:
            coupled = True
        else:
            raise Exception('tapas:hgf:HgfBinaryMab:CoupledOnlyForTwo','Coupled updating can only be configured for 2 bandits.')

    p_dict = {}
    p_dict['mu_0']    = p[0:l]
    p_dict['sa_0']    = p[l:2*l]
    p_dict['phi']    = p[2*l:3*l]
    p_dict['m']    = p[3*l:4*l]
    p_dict['rho']     = p[2*l:3*l]
    p_dict['ka']      = p[3*l:4*l]
    p_dict['om']      = p[4*l:5*l-1]
    with np.errstate(divide='ignore'): p_dict['th'] = np.exp(p[6*l-2])

    # Add dummy zeroth trial
    u = np.insert(r['u'], 0, 0)
    y = np.insert(r['u'], 1, 0)
    n = len(u)
    # Construct time axis
    if r['c_prc']['irregular_intervals']:
        t = r['u'][1,:]  # make sure this deminsion is [2, x] second being time
    else:
        t = np.ones(n)
    
    # Initialize updated quantities
    
    # Representations
    mu = np.empty((n, l, b)) * np.nan
    pi = np.empty((n,l,b)) * np.nan
    # Other quantities
    muhat = np.empty((n,l,b)) * np.nan
    pihat = np.empty((n,l,b)) * np.nan
    v = np.empty((n,l)) * np.nan
    w = np.empty((n,l - 1)) * np.nan
    da = np.empty((n,l)) * np.nan
    # Representation priors
    # Note: first entries of the other quantities remain
    # NaN because they are undefined and are thrown away
    # at the end; their presence simply leads to consistent
    # trial indices.
    mu[0,0,:] = _sgm(p_dict['mu_0'][1],1)
    muhat[0,0,:] = mu[0,0,:]
    pihat[0,0,:] = 0
    pi[0,0,:] = np.Inf
    mu[0,1:,:] = np.matlib.repmat(p_dict['mu_0'][1:],[0,0,b])
    pi[1,1:,:] = np.matlib.repmat(1./p_dict['sa_0'][1:],[0,0,b])
    # Pass through representation update loop
    for k in range(1, n):
        if not k in r['ign']:
            ######################
            # Effect of input u(k)
            ######################
            # 2nd level prediction
            muhat[k,l,:] = mu[k-1,2,:] + t[k] * p_dict['phi'][1] * (p_dict['m'][1] - mu[k-2,1,:])
            # 1st level
            # ~~~~~~~~~
            # Prediction
            muhat[k,0,:] = _sgm(p_dict['ka'][0] * muhat[k-1,1,:],1)
            # Precision of prediction
            pihat[k,0,:] = 1 / (muhat[k,0,:]* (1 - muhat[k,0,:]))
            # Updates
            pi[k,0,:] = pihat[k,0,:]
            pi[k,0,y(k)] = np.Inf

            # TODO ...            
    #         mu[k,1,:] = muhat(k,1,:)
    #         mu[k,1,y[k]] = u(k)
    #         # Prediction error
    #         da[k,1] = mu(k,1,y(k)) - muhat(k,1,y(k))
    #         # 2nd level
    #         # ~~~~~~~~~
    #         # Prediction: see above
    #         # Precision of prediction
    #         pihat[k,2,:] = 1 / (1 / pi(k - 1,2,:) + np.exp(ka(2) * mu(k - 1,3,:) + om(2)))
    #         # Updates
    #         pi[k,2,:] = pihat(k,2,:) + ka(1) ** 2 / pihat(k,1,:)
    #         mu[k,2,:] = muhat(k,2,:)
    #         mu[k,2,y[k]] = muhat(k,2,y(k)) + ka(1) / pi(k,2,y(k)) * da(k,1)
    #         # Volatility prediction error
    #         da[k,2] = (1 / pi(k,2,y(k)) + (mu(k,2,y(k)) - muhat(k,2,y(k))) ** 2) * pihat(k,2,y(k)) - 1
    #         if l > 3:
    #             # Pass through higher levels
    #         # ~~~~~~~~~~~~~~~~~~~~~~~~~~
    #             for j in np.arange(3,l - 1+1).reshape(-1):
    #                 # Prediction
    #                 muhat[k,j,:] = mu(k - 1,j,:) + t(k) * phi(j) * (m(j) - mu(k - 1,j))
    #                 # Precision of prediction
    #                 pihat[k,j,:] = 1 / (1 / pi(k - 1,j,:) + t(k) * np.exp(ka(j) * mu(k - 1,j + 1,:) + om(j)))
    #                 # Weighting factor
    #                 v[k,j - 1] = t(k) * np.exp(ka(j - 1) * mu(k - 1,j,y(k)) + om(j - 1))
    #                 w[k,j - 1] = v(k,j - 1) * pihat(k,j - 1,y(k))
    #                 # Updates
    #                 pi[k,j,:] = pihat(k,j,:) + 1 / 2 * ka(j - 1) ** 2 * w(k,j - 1) * (w(k,j - 1) + (2 * w(k,j - 1) - 1) * da(k,j - 1))
    #                 if pi(k,j,1) <= 0:
    #                     raise Exception('tapas:hgf:NegPostPrec','Negative posterior precision. Parameters are in a region where model assumptions are violated.')
    #                 mu[k,j,:] = muhat(k,j,:) + 1 / 2 * 1 / pi(k,j) * ka(j - 1) * w(k,j - 1) * da(k,j - 1)
    #                 # Volatility prediction error
    #                 da[k,j] = (1 / pi(k,j,y(k)) + (mu(k,j,y(k)) - muhat(k,j,y(k))) ** 2) * pihat(k,j,y(k)) - 1
    #         # Last level
    #         # ~~~~~~~~~~
    #         # Prediction
    #         muhat[k,l,:] = mu(k - 1,l,:) + t(k) * phi(l) * (m(l) - mu(k - 1,l))
    #         # Precision of prediction
    #         pihat[k,l,:] = 1 / (1 / pi(k - 1,l,:) + t(k) * th)
    #         # Weighting factor
    #         v[k,l] = t(k) * th
    #         v[k,l - 1] = t(k) * np.exp(ka(l - 1) * mu(k - 1,l,y(k)) + om(l - 1))
    #         w[k,l - 1] = v(k,l - 1) * pihat(k,l - 1,y(k))
    #         # Updates
    #         pi[k,l,:] = pihat(k,l,:) + 1 / 2 * ka(l - 1) ** 2 * w(k,l - 1) * (w(k,l - 1) + (2 * w(k,l - 1) - 1) * da(k,l - 1))
    #         if pi(k,l,1) <= 0:
    #             raise Exception('tapas:hgf:NegPostPrec','Negative posterior precision. Parameters are in a region where model assumptions are violated.')
    #         mu[k,l,:] = muhat(k,l,:) + 1 / 2 * 1 / pi(k,l,:) * ka(l - 1) * w(k,l - 1) * da(k,l - 1)
    #         # Volatility prediction error
    #         da[k,l] = (1 / pi(k,l,y(k)) + (mu(k,l,y(k)) - muhat(k,l,y(k))) ** 2) * pihat(k,l,y(k)) - 1
    #         if coupled == True:
    #             if y(k) == 1:
    #                 mu[k,1,2] = 1 - mu(k,1,1)
    #                 mu[k,2,2] = tapas_logit(1 - tapas_sgm(mu(k,2,1),1),1)
    #             else:
    #                 if y(k) == 2:
    #                     mu[k,1,1] = 1 - mu(k,1,2)
    #                     mu[k,2,1] = tapas_logit(1 - tapas_sgm(mu(k,2,2),1),1)
    #     else:
    #         mu[k,:,:] = mu(k - 1,:,:)
    #         pi[k,:,:] = pi(k - 1,:,:)
    #         muhat[k,:,:] = muhat(k - 1,:,:)
    #         pihat[k,:,:] = pihat(k - 1,:,:)
    #         v[k,:] = v(k - 1,:)
    #         w[k,:] = w(k - 1,:)
    #         da[k,:] = da(k - 1,:)
    
    # # Remove representation priors
    # mu[1,:,:] = []
    # pi[1,:,:] = []
    # # Check validity of trajectories
    # if np.any(np.isnan(mu)) or np.any(np.isnan(pi)):
    #     raise Exception('tapas:hgf:VarApproxInvalid','Variational approximation invalid. Parameters are in a region where model assumptions are violated.')
    # else:
    #     # Check for implausible jumps in trajectories
    #     dmu = np.diff(mu(:,np.arange(2,end()+1)))
    #     dpi = np.diff(pi(:,np.arange(2,end()+1)))
    #     rmdmu = np.matlib.repmat(np.sqrt(mean(dmu ** 2)),len(dmu),1)
    #     rmdpi = np.matlib.repmat(np.sqrt(mean(dpi ** 2)),len(dpi),1)
    #     jumpTol = 16
    #     if np.any(np.abs(dmu) > jumpTol * rmdmu) or np.any(np.abs(dpi) > jumpTol * rmdpi):
    #         raise Exception('tapas:hgf:VarApproxInvalid','Variational approximation invalid. Parameters are in a region where model assumptions are violated.')
    
    # # Remove other dummy initial values
    # muhat[1,:,:] = []
    # pihat[1,:,:] = []
    # v[1,:] = []
    # w[1,:] = []
    # da[1,:] = []
    # y[1] = []
    # # Responses on regular trials
    # yreg = y
    # yreg[irr] = []
    # # Implied learning rate at the first level
    # mu2 = np.squeeze(mu(:,2,:))
    # mu2[irr,:] = []
    # mu2obs = mu2(sub2ind(mu2.shape,np.transpose((np.arange(1,mu2.shape[1-1]+1))),yreg))
    # mu1hat = np.squeeze(muhat(:,1,:))
    # mu1hat[irr,:] = []
    # mu1hatobs = mu1hat(sub2ind(mu1hat.shape,np.transpose((np.arange(1,mu1hat.shape[1-1]+1))),yreg))
    # upd1 = tapas_sgm(ka(1) * mu2obs,1) - mu1hatobs
    # dareg = da
    # dareg[irr,:] = []
    # lr1reg = upd1 / dareg(:,1)
    # lr1 = np.full([n - 1,1],np.nan)
    # lr1[setdiff[np.arange[1,n - 1+1],irr]] = lr1reg
    # # Create result data structure
    # traj = struct
    # traj.mu = mu
    # traj.sa = 1.0 / pi
    # traj.muhat = muhat
    # traj.sahat = 1.0 / pihat
    # traj.v = v
    # traj.w = w
    # traj.da = da
    # # Updates with respect to prediction
    # traj.ud = mu - muhat
    # # Psi (precision weights on prediction errors)
    # psi = np.full([n - 1,l],np.nan)
    # pi2 = np.squeeze(pi(:,2,:))
    # pi2[irr,:] = []
    # pi2obs = pi2(sub2ind(pi2.shape,np.transpose((np.arange(1,pi2.shape[1-1]+1))),yreg))
    # psi[setdiff[np.arange[1,n - 1+1],irr],2] = 1.0 / pi2obs
    # for i in np.arange(3,l+1).reshape(-1):
    #     pihati = np.squeeze(pihat(:,i - 1,:))
    #     pihati[irr,:] = []
    #     pihatiobs = pihati(sub2ind(pihati.shape,np.transpose((np.arange(1,pihati.shape[1-1]+1))),yreg))
    #     pii = np.squeeze(pi(:,i,:))
    #     pii[irr,:] = []
    #     piiobs = pii(sub2ind(pii.shape,np.transpose((np.arange(1,pii.shape[1-1]+1))),yreg))
    #     psi[setdiff[np.arange[1,n - 1+1],irr],i] = pihatiobs / piiobs
    
    # traj.psi = psi
    # # Epsilons (precision-weighted prediction errors)
    # epsi = np.full([n - 1,l],np.nan)
    # epsi[:,np.arange[2,l+1]] = np.multiply(psi(:,np.arange(2,l+1)),da(:,np.arange(1,l - 1+1)))
    # traj.epsi = epsi
    # # Full learning rate (full weights on prediction errors)
    # wt = np.full([n - 1,l],np.nan)
    # wt[:,1] = lr1
    # wt[:,2] = psi(:,2)
    # wt[:,np.arange[3,l+1]] = np.multiply(1 / 2 * (v(:,np.arange(2,l - 1+1)) * diag(ka(np.arange(2,l - 1+1)))),psi(:,np.arange(3,l+1)))
    # traj.wt = wt
    # # Create matrices for use by the observation model
    # np.infStates = np.full([n - 1,l,b,4],np.nan)
    # np.infStates[:,:,:,1] = traj.muhat
    # np.infStates[:,:,:,2] = traj.sahat
    # np.infStates[:,:,:,3] = traj.mu
    # np.infStates[:,:,:,4] = traj.sa
    # return traj,infStates

def hgf_binary(r, p, trans=False):
    """calculate trajectorie of agent's representations under HGF"""
    
    if trans: p = r['c_prc']['transp_prc_fun'](r, p) # transform parameters to native space
    p_dict = _unpack_para(p, r)            # get parameters unpacked
    u = np.insert(r['u'], 0, 0)            # add zeroth trial
    n = len(u)                             # length of trials inc. prior
    l = r['c_prc']['n_levels']             # get number of levels
    
    # set time dim for irregular intervals, or set to ones for reggular
    if r['c_prc']['irregular_intervals']:
        t = r['u'][1,:]  # make sure this deminsion is [2, x] second being time
    else:
        t = np.ones(n)
    
    # initialize what to update
    mu = np.empty((n, l)) * np.nan         # mu represnetation
    pi = np.empty((n, l)) * np.nan         # pi representation
    mu_hat = np.empty((n, l)) * np.nan     # mu^ quantity
    pi_hat = np.empty((n, l)) * np.nan     # pi^ quantity
    v = np.empty((n, l)) * np.nan           
    w = np.empty((n, l-1)) * np.nan
    da = np.empty((n, l)) * np.nan         # prediction errors
    
    # initial priors, for all remaining this will remain nan
    mu[0,0] = _sgm(p_dict['mu_0'][0], 1)
    mu[0,1:] = p_dict['mu_0'][1:]
    pi[0,0] = np.inf
    pi[0,1:] = p_dict['sa_0'][1:]**-1   # silence warning, inf resulst for sim model is fine
    
    # represnetation update loop!
    for trial in range(1, n):
        
        # check if trail has to be ignored
        if not trial in r['ign']:

            # make second level initial pred. (weighted by time)
            mu_hat[trial,1] = mu[trial-1,1] + (t[trial]*p_dict['rho'][1])     

            ####1ST LVL####
            # make first level pred using second level pred. 
            mu_hat[trial,0] = _sgm(p_dict['ka'][0] * mu_hat[trial,1], 1)  # prediction
            pi_hat[trial,0] = 1 / (mu_hat[trial,0] * (1-mu_hat[trial,0])) # precision of pred

            # update
            pi[trial,0] = np.inf
            mu[trial,0] = u[trial]

            # prediction error
            da[trial,0] = mu[trial,0] - mu_hat[trial,0]
            
            ####LOOP OVER LEVELS - TAKING SPECIAL CARE OF 2ND AND LAST LEVEL####
            for lvl in range(1, l):

                # for level 2
                if lvl < 2:
                    
                    # precision of prediction
                    pi_hat[trial,lvl] = (pi[trial-1,lvl]**-1 + t[trial] 
                                         * np.exp(p_dict['ka'][lvl] * 
                                                  mu[trial-1, lvl+1] +
                                                  p_dict['om'][lvl]))**-1

                    # update
                    pi[trial,1] = pi_hat[trial,1] + p_dict['ka'][0]**2 / pi_hat[trial,0]
                    mu[trial,1] = mu_hat[trial,1] + p_dict['ka'][0] / pi[trial,1] * da[trial,0]

                elif lvl >= 2: # all higher levels, scales above 3

                    # prediction (identical to initial pred)
                    mu_hat[trial,lvl] = mu[trial-1,lvl] + (t[trial]*p_dict['rho'][lvl])
                    
                    if lvl == l-1: # for last level
                        
                        # precision of prediction (now using -th-)
                        pi_hat[trial,l-1] = (pi[trial-1,l-1]**-1 + t[trial] * p_dict['th'])**-1
                        
                        # weighting factor
                        v[trial,l-1] = t[trial] * p_dict['th']
                        v[trial,l-2] = t[trial] * np.exp(p_dict['ka'][l-2] * mu[trial-1, l-1] + p_dict['om'][l-2])
                        w[trial,l-2] = v[trial,l-2] * pi_hat[trial,l-2]

                    else: # intermediate (not last/first) levels
                        
                        # precision of prediction (now using -th-)
                        pi_hat[trial,l-1] = (pi[trial-1,l-1]**-1 + t[trial] * p_dict['th'])**-1
                        
                        # weighting
                        v[trial, lvl-1] = t[trial] * np.exp(p_dict['ka'][lvl-1] * 
                                                            mu[trial-1, lvl] + 
                                                            p_dict['om'][lvl-1])
                        w[trial, lvl-1] = v[trial, lvl-1] * pi_hat[trial, lvl-1]

                        
                    ##---------------------------------------------------------------------------------------------------------##   
                    # updates using enhanced hgf binary model
                    if 'ehgf' in r['c_prc']['model']:
                        mu[trial,lvl] = mu_hat[trial,lvl] + \
                                        0.5 * pi_hat[trial,lvl]**-1 * \
                                        p_dict['ka'][lvl-1] * \
                                        w[trial,lvl-1] * \
                                        da[trial,lvl-1]
                        # update precision depending on mean update
                        vv = t[trial] * np.exp(p_dict['ka'][lvl-1]* 
                                               mu[trial, lvl] + 
                                               p_dict['om'][lvl-1])
                        pim_hat = (pi[trial-1, lvl-1]**-1 + vv)**-1
                        ww = vv * pim_hat
                        rr = (vv - pi[trial-1, lvl-1]**-1) * pim_hat
                        dd = (pi[trial, lvl-1]**-1 + (mu[trial, lvl-1] - mu_hat[trial, lvl-1])**2) * pim_hat -1
                        # update pi, add 0 if equation is lower then 0
                        pi[trial, lvl] = pi_hat[trial, lvl] + np.maximum(0, 0.5* p_dict['ka'][lvl-1]**2 * ww * (ww + rr * dd))
                    # we default back to standard hgf
                    else:
                        pi[trial,lvl] = pi_hat[trial,lvl] + \
                                        0.5 * p_dict['ka'][lvl-1]**2 * \
                                        w[trial,lvl-1] * \
                                        (w[trial,lvl-1] + (2 *w[trial,lvl-1] -1) *da[trial,lvl-1])
                        mu[trial,lvl] = mu_hat[trial,lvl] + \
                                        0.5 * pi[trial,lvl]**-1 * \
                                        p_dict['ka'][lvl-1] * \
                                        w[trial,lvl-1] * \
                                        da[trial,lvl-1]
                    ##---------------------------------------------------------------------------------------------------------## 
                        
                # prediction error    
                da[trial,lvl] = (pi[trial,lvl]**-1 + (mu[trial,lvl] - mu_hat[trial, lvl])**2)  *  pi_hat[trial,lvl] -1

        # if trial is ignored we do not update anything
        else: 
            mu[trial,:] = mu[trial-1,:]
            pi[trial,:] = pi[trial-1,:]

            mu[trial,:] = mu[trial-1,:]
            pi[trial,:] = pi[trial-1,:]

            v[trial,:]  = v[trial-1,:]
            w[trial,:]  = w[trial-1,:]
            da[trial,:] = da[trial-1,:]
    
    # learing rates
    sgmmu2    = _sgm(p_dict['ka'][0] * mu[:,1], 1)
    dasgmmu2  = u - sgmmu2   
    lr1       = np.divide(np.diff(sgmmu2), dasgmmu2[1:n])
    lr1[da[1:n,1]==0] = 0
    
    # remove rep. priors and dummy value
    mu       = np.delete(mu,0, axis=0)
    pi       = np.delete(pi,0, axis=0)
    mu_hat   = np.delete(mu_hat,0, axis=0)
    pi_hat   = np.delete(pi_hat,0, axis=0)
    v        = np.delete(v,0, axis=0)
    w        = np.delete(w,0, axis=0)
    da       = np.delete(da,0, axis=0)
    
    # store results in dict
    traj = {}
    traj['mu']      = mu
    traj['sa']      = pi**-1
    traj['mu_hat']  = mu_hat
    traj['sa_hat']  = pi_hat**-1
    traj['v']       = v
    traj['w']       = w
    traj['da']      = da
    traj['ud']      = mu - mu_hat  # updates with respect to prediction
    
    # precision weight on pred error
    psi          = np.empty([n-1,l])
    psi[:]       = np.nan
    psi[:,1]     = pi[:,1]**-1
    psi[:,2:l]   = np.divide(pi_hat[:,1:l-1], pi[:,2:l])
    traj['psi']  = psi
    
    # epsions (precision weighted pred. errors)
    epsi         = np.empty([n-1,l])
    epsi[:]      = np.nan
    epsi[:,1:l]  = np.multiply(psi[:,1:l], da[:,:l-1])
    traj['epsi'] = epsi
    
    # learning rate
    wt           = np.empty([n-1,l])
    wt[:]        = np.nan    
    wt[:,0]      = lr1
    wt[:,1]      = psi[:,1]
    wt[:,2:l]    = np.multiply(0.5 * (v[:,1:l-1] * 
                                      np.diagonal(p_dict['ka'][1:l-1].reshape(1,len(p_dict['ka'][1:l-1])))), 
                                      psi[:,2:l])
    traj['wt']   = wt
    
    # matrics observational model DIMENSIONALLITY PROBLEMS
    infStates    = np.empty([n-1,l,4])
    infStates[:] = np.nan
    infStates[:,:,0]  = traj['mu_hat']
    infStates[:,:,1]  = traj['sa_hat']
    infStates[:,:,2]  = traj['mu']
    infStates[:,:,3]  = traj['sa']
    return([traj, infStates])

def ehgf_binary(r, p, trans=False):
    """Allias function for hgf_binary with r['c_prc']['model'] set to 'ehgf_binary'"""
    # set model manually to ehgf_binary for enhanced model
    r['c_prc']['model'] = 'ehgf_binary'
    return(hgf_binary(r, p, trans=trans))



def hgf(r, p, trans=False):
    """calculate trajectorie of agent's representations under HGF"""
    
    if trans: p = r['c_prc']['transp_prc_fun'](r, p) # transform parameters to native space
    p_dict = _unpack_para(p, r)            # get parameters unpacked
    u = np.insert(r['u'], 0, 0)            # add zeroth trial
    n = len(u)                             # length of trials inc. prior
    l = r['c_prc']['n_levels']             # get number of levels
    
    # set time dim for irregular intervals, or set to ones for reggular
    if r['c_prc']['irregular_intervals']:
        t = r['u'][1,:]  # make sure this deminsion is [2, x] second being time
    else:
        t = np.ones(n)
    
    # initialize what to update
    mu = np.empty((n, l)) * np.nan         # mu represnetation
    pi = np.empty((n, l)) * np.nan         # pi representation
    mu_hat = np.empty((n, l)) * np.nan     # mu^ quantity
    pi_hat = np.empty((n, l)) * np.nan     # pi^ quantity
    v = np.empty((n, l)) * np.nan           
    w = np.empty((n, l-1)) * np.nan
    da = np.empty((n, l)) * np.nan         # prediction errors
    dau = np.empty((n, 1)) * np.nan
    
    # initial priors, for all remaining this will remain nan
    mu[0,:] = p_dict['mu_0']
    pi[0,:] = p_dict['sa_0']**-1
    
    # represnetation update loop!
    for trial in range(1, n):
        
        # check if trail has to be ignored
        if not trial in r['ign']:  

            ####1ST LVL####
            # make first level pred, and precision of prediction
            mu_hat[trial,0] = mu[trial-1, 0] + t[trial] * p_dict['rho'][0]
            pi_hat[trial,0] = (pi[trial-1, 0]**-1 + t[trial] * np.exp(p_dict['ka'][0] *
                                                                     mu[trial-1, 1] + 
                                                                     p_dict['om'][0]))**-1
            
            # pred. error input
            dau[trial] = u[trial] - mu_hat[trial, 0]

            # update
            pi[trial,0] = pi_hat[trial, 0] + p_dict['al']**-1
            mu[trial,0] = mu_hat[trial, 0] + pi_hat[trial, 0]**-1 * \
                          (pi_hat[trial, 0]**-1 + p_dict['al'])**-1 * \
                          dau[trial]
            
            # volatility prediction error
            da[trial,0] = (pi[trial,0]**-1 + (mu[trial,0] - mu_hat[trial,0])**2) * \
                          pi_hat[trial,0] - 1
            
            ####LOOP OVER LEVELS - TAKING SPECIAL CARE OF 2ND AND LAST LEVEL####
            for lvl in range(1, l):

                # prediction (identical to initial pred)
                mu_hat[trial,lvl] = mu[trial-1,lvl] + (t[trial]*p_dict['rho'][lvl])

                if lvl != l-1: # for last level
                    # precision of prediction
                    pi_hat[trial,lvl] = (pi[trial-1,lvl]**-1 + t[trial] 
                                         * np.exp(p_dict['ka'][lvl] * 
                                                  mu[trial-1, lvl+1] +
                                                  p_dict['om'][lvl]))**-1
                    
                    # weighting
                    v[trial, lvl-1] = t[trial] * np.exp(p_dict['ka'][lvl-1] * 
                                                        mu[trial-1, lvl] + 
                                                        p_dict['om'][lvl-1])
                    w[trial, lvl-1] = v[trial, lvl-1] * pi_hat[trial, lvl-1]

                else: # intermediate (not last/first) levels
                   # precision of prediction (now using -th-)
                    pi_hat[trial,l-1] = (pi[trial-1,l-1]**-1 + t[trial] * p_dict['th'])**-1  

                    # weighting factor
                    v[trial,l-1] = t[trial] * p_dict['th']
                    v[trial,l-2] = t[trial] * np.exp(p_dict['ka'][l-2] * mu[trial-1, l-1] + p_dict['om'][l-2])
                    w[trial,l-2] = v[trial,l-2] * pi_hat[trial,l-2]
                    

                ##---------------------------------------------------------------------------------------------------------##    
                # UPDATES USING ENCHANCED HGF MODEL
                if 'ehgf' in r['c_prc']['model']:
                    mu[trial,lvl] = mu_hat[trial,lvl] + \
                                    0.5 * pi_hat[trial,lvl]**-1 * \
                                    p_dict['ka'][lvl-1] * \
                                    w[trial,lvl-1] * \
                                    da[trial,lvl-1]
                    # update precision depending on mean update
                    vv = t[trial] * np.exp(p_dict['ka'][lvl-1]* 
                                           mu[trial, lvl] + 
                                           p_dict['om'][lvl-1])
                    pim_hat = (pi[trial-1, lvl-1]**-1 + vv)**-1
                    ww = vv * pim_hat
                    rr = (vv - pi[trial-1, lvl-1]**-1) * pim_hat
                    dd = (pi[trial, lvl-1]**-1 + (mu[trial, lvl-1] - mu_hat[trial, lvl-1])**2) * pim_hat -1
                    # update pi, add 0 if equation is lower then 0
                    pi[trial, lvl] = pi_hat[trial, lvl] + np.maximum(0, 0.5* p_dict['ka'][lvl-1]**2 * ww * (ww + rr * dd))
                    
                # OR WE DEFAULT TO STANDARD HGF MODEL
                else:
                    pi[trial,lvl] = pi_hat[trial,lvl] + \
                                    0.5 * p_dict['ka'][lvl-1]**2 * \
                                    w[trial,lvl-1] * \
                                    (w[trial,lvl-1] + (2 *w[trial,lvl-1] -1) *da[trial,lvl-1])
                    mu[trial,lvl] = mu_hat[trial,lvl] + \
                                    0.5 * pi[trial,lvl]**-1 * \
                                    p_dict['ka'][lvl-1] * \
                                    w[trial,lvl-1] * \
                                    da[trial,lvl-1]
                ##---------------------------------------------------------------------------------------------------------## 
                        
                # prediction error    
                da[trial,lvl] = (pi[trial,lvl]**-1 + (mu[trial,lvl] - mu_hat[trial, lvl])**2)  *  pi_hat[trial,lvl] -1

        # if trial is ignored we do not update anything
        else: 
            mu[trial,:] = mu[trial-1,:]
            pi[trial,:] = pi[trial-1,:]

            mu[trial,:] = mu[trial-1,:]
            pi[trial,:] = pi[trial-1,:]

            v[trial,:]  = v[trial-1,:]
            w[trial,:]  = w[trial-1,:]
            da[trial,:] = da[trial-1,:]
    
    # remove rep. priors and dummy value
    mu       = np.delete(mu,0, axis=0)
    pi       = np.delete(pi,0, axis=0)
    mu_hat   = np.delete(mu_hat,0, axis=0)
    pi_hat   = np.delete(pi_hat,0, axis=0)
    v        = np.delete(v,0, axis=0)
    w        = np.delete(w,0, axis=0)
    da       = np.delete(da,0, axis=0)
    dau      = np.delete(dau, 0)
    
    # store results in dict
    traj = {}
    traj['mu']      = mu
    traj['sa']      = pi**-1
    traj['mu_hat']  = mu_hat
    traj['sa_hat']  = pi_hat**-1
    traj['v']       = v
    traj['w']       = w
    traj['da']      = da
    traj['dau']     = dau.reshape(len(dau),1)
    traj['ud']      = mu - mu_hat  # updates with respect to prediction
    
    # precision weight on pred error
    psi          = np.empty([n-1,l])
    psi[:]       = np.nan
    psi[:,0]     = (p_dict['al'] * pi[:,0])**-1
    psi[:,1:l]   = np.divide(pi_hat[:,0:l-1], pi[:,1:l])
    traj['psi']  = psi
    
    # epsions (precision weighted pred. errors)
    epsi         = np.empty([n-1,l])
    epsi[:]      = np.nan
    epsi[:,0]    = np.multiply(psi[:,0], dau)
    epsi[:,1:l]  = np.multiply(psi[:,1:l], da[:,:l-1])
    traj['epsi'] = epsi
    
    # learning rate
    wt           = np.empty([n-1,l])
    wt[:]        = np.nan    
    wt[:,0]      = psi[:,0]
    wt[:,1:l]    = np.multiply(0.5 * (v[:,0:l-1] * 
                                      np.diagonal(p_dict['ka'][0:l-1].reshape(1,len(p_dict['ka'][0:l-1])))), 
                                      psi[:,1:l])
    traj['wt']   = wt
    
    # matrics observational model DIMENSIONALLITY PROBLEMS
    infStates    = np.empty([n-1,l,4])
    infStates[:] = np.nan
    infStates[:,:,0]  = traj['mu_hat']
    infStates[:,:,1]  = traj['sa_hat']
    infStates[:,:,2]  = traj['mu']
    infStates[:,:,3]  = traj['sa']
    return([traj, infStates])

def ehgf(r, p, trans=False):
    """Allias function for hgf with r['c_prc']['model'] set to 'ehgf'"""
    # set model manually to ehgf_binary for enhanced model
    r['c_prc']['model'] = 'ehgf'
    return(hgf(r, p, trans=trans))


## Transform parameters

def hgf_transp(r, ptrans):
    """transform parameters to native space"""
    # initialize nan array
    pvec = np.empty(len(ptrans))
    pvec[:] = np.nan
    
    # get number of levels
    l = r['c_prc']['n_levels']
    
    # trans to native space
    pvec[0:l]          = ptrans[0:l]
    pvec[l:2*l]        = np.exp(ptrans[l:2*l])
    pvec[2*l:3*l]      = ptrans[2*l:3*l]
    pvec[3*l:4*l-1]    = np.exp(ptrans[3*l:4*l-1])
    pvec[4*l-1:5*l-1]  = ptrans[4*l-1:5*l-1]
    # for continuus hgf
    if not 'binary' in r['c_prc']['model']:
        pvec[5*l-1]    = np.exp(ptrans[5*l-1])
    return(pvec)

def hgf_ar1_binary_mab_transp(r = None,ptrans = None): 
    # --------------------------------------------------------------------------------------------------
            # Copyright (C) 2013 Christoph Mathys, TNU, UZH & ETHZ
    
    # This file is part of the HGF toolbox, which is released under the terms of the GNU General Public
            # Licence (GPL), version 3. You can redistribute it and/or modify it under the terms of the GPL
            # (either version 3 or, at your option, any later version). For further details, see the file
            # COPYING or <http://www.gnu.org/licenses/>.
    
    pvec = np.full([1,len(ptrans)],np.nan)
    pstruct = {}
    l = r.c_prc.n_levels
    pvec[np.arange[1,l+1]] = ptrans(np.arange(1,l+1))
    
    pstruct.mu_0 = pvec(np.arange(1,l+1))
    pvec[np.arange[l + 1,2 * l+1]] = np.exp(ptrans(np.arange(l + 1,2 * l+1)))
    
    pstruct.sa_0 = pvec(np.arange(l + 1,2 * l+1))
    pvec[np.arange[2 * l + 1,3 * l+1]] = tapas_sgm(ptrans(np.arange(2 * l + 1,3 * l+1)),1)
    
    pstruct.phi = pvec(np.arange(2 * l + 1,3 * l+1))
    pvec[np.arange[3 * l + 1,4 * l+1]] = ptrans(np.arange(3 * l + 1,4 * l+1))
    
    pstruct.m = pvec(np.arange(3 * l + 1,4 * l+1))
    pvec[np.arange[4 * l + 1,5 * l - 1+1]] = np.exp(ptrans(np.arange(4 * l + 1,5 * l - 1+1)))
    
    pstruct.ka = pvec(np.arange(4 * l + 1,5 * l - 1+1))
    pvec[np.arange[5 * l,6 * l - 1+1]] = ptrans(np.arange(5 * l,6 * l - 1+1))
    
    pstruct.om = pvec(np.arange(5 * l,6 * l - 1+1))
    return pvec,pstruct

def unitsq_sqm_transp(r, ptrans):
    """transform parameters to native space"""
    # initialize nan array
    pvec = np.empty(len(ptrans))
    pvec[:] = np.nan
    pstruct = {}
    
    # get _ze_
    pvec[0] = np.exp(ptrans)
    pstruct['ze'] = pvec[0]
    return([pvec, pstruct])

def softmax_mu3_transp(r, ptrans):
  return {
      'pvec': np.array([]),
      'pstruct': {}
  }


## Calculations optimization

def bayes_optimal_binary(r, infStates, ptrans):
    """calculate the log-probabilitie of inputs given predictions"""
    # initialize arrays
    n        = infStates.shape[0]
    logp     = np.empty(n)
    logp[:]  = np.nan
    y_hat    = np.empty(n)
    y_hat[:] = np.nan
    res      = np.empty(n)
    res[:]   = np.nan
    
    # remove irregulars 
    u = r['u'][:]                
    u = np.delete(u, r['irr'])     # for inputs
    x = infStates[:,0,0]
    x = np.delete(x, r['irr'])     # and for predictions

    # calculate log-prob for remaining trials
    reg       = ~np.isin(np.arange(0, len(u)), r['irr'])
    logp[reg] = np.multiply(u, np.log(x)) + np.multiply(1-u, np.log(1-x))
    y_hat[reg] = x
    res[reg]  = np.divide(u-x, np.sqrt(np.multiply(x, 1-x)))
    return(logp, y_hat, res)


def bayes_optimal(r, infStates, ptrans):
    """calculate the log-probabilitie of inputs given predictions"""
    # initialize arrays
    n        = infStates.shape[0]
    logp     = np.empty(n)
    logp[:]  = np.nan
    y_hat    = np.empty(n)
    y_hat[:] = np.nan
    res      = np.empty(n)
    res[:]   = np.nan
    
    # remove irregulars 
    u = r['u'][:]                
    u = np.delete(u, r['irr'])     # for inputs

    # predictions
    mu1hat = infStates[:,0,0]
    mu1hat = np.delete(mu1hat, r['irr'])
    
    # variance {inverse precision} of prediction
    sa1hat = infStates[:,0,1]
    sa1hat = np.delete(sa1hat, r['irr'])
    
    # calculate log-prob for remaining trials
    reg        = ~np.isin(np.arange(0, len(u)), r['irr'])
    logp[reg]  = -0.5 * np.log((8*np.arctan(1)) * sa1hat) - \
                        np.divide((u - mu1hat)**2, 2*sa1hat)
    y_hat[reg] = mu1hat
    res[reg]   = u-mu1hat
    return(logp, y_hat, res)


## calculations for observational models

def gaussian_obs(r, infStates, ptrans):
    """Calculate log-probabilities of y=1 using gaussian noise model"""
    # initialize arrays
    n        = infStates.shape[0]
    logp     = np.empty(n)
    logp[:]  = np.nan
    y_hat    = np.empty(n)
    y_hat[:] = np.nan
    res      = np.empty(n)
    res[:]   = np.nan
    
    # remove irregulars 
    u = r['u'][:]                
    u = np.delete(u, r['irr'])     # for inputs
    
    # zeta to native
    ze = np.exp(ptrans[0])
    
    # remove irregulars
    x = infStates[:,0,0]
    x = np.delete(x, r['irr'])     # and for predictions    
    y = r['y'][:]                
    y = np.delete(y, r['irr'])     # for perception
  
    # calculate log-prob for remaining trials
    reg        = ~np.isin(np.arange(0, len(u)), r['irr']) 
    logp[reg]  = -0.5 * np.log((8*np.arctan(1)) * ze) - \
                        np.divide((y - x)**2, 2*ze)
    y_hat[reg] = x
    res[reg]   = y-x
    
    return(logp, y_hat, res)


def unitsq_sgm(r, infStates, ptrans):
    """Calculate log-probabilities of y=1 using unit-sq sigmoid model"""
    # initialize arrays
    n        = infStates.shape[0]
    logp     = np.empty(n)
    logp[:]  = np.nan
    y_hat    = np.empty(n)
    y_hat[:] = np.nan
    res      = np.empty(n)
    res[:]   = np.nan
    
    # remove irregulars 
    u = r['u'][:]                
    u = np.delete(u, r['irr'])     # for inputs
    
    # zeta to native
    ze = np.exp(ptrans[0])
    
    # remove irregulars
    x = infStates[:,0,0]
    x = np.delete(x, r['irr'])     # and for predictions    
    y = r['y'][:]                
    y = np.delete(y, r['irr'])     # for perception
    
    # logtransform 
    logx                = np.log(x)
    logx[1-x < 1e-4]    = np.log1p(x-1)[1-x < 1e-4]   # so we dont get any rounding errors later on
    logminx             = np.log(1-x)
    logminx[x < 1e-4]   = np.log1p(-x)[x < 1e-4]      # so we dont get any rounding errors later on
  
    # calculate log-prob for remaining trials
    reg        = ~np.isin(np.arange(0, len(u)), r['irr']) 
    logp[reg]  = np.multiply(np.multiply(y, ze),
                             logx - logminx) + np.multiply(ze, logminx) - np.log((1-x)**ze + x**ze)
    y_hat[reg] = x
    res[reg]   = np.divide(y-x,
                           np.sqrt(np.multiply(x,
                                               1-x)))
    
    return(logp, y_hat, res)

## helper functions

def sub2ind(array_shape, rows, cols):
    ind = rows*array_shape[1] + cols
    ind[ind < 0] = -1
    ind[ind >= array_shape[0]*array_shape[1]] = -1
    return ind

def ismember(a_vec, b_vec):

    bool_ind = np.isin(a_vec, b_vec)
    common = a[bool_ind]
    common_unique, common_inv = np.unique(common, return_inverse=True)
    b_unique, b_ind = np.unique(b_vec, return_index=True)
    common_ind = b_ind[np.isin(b_unique, common_unique, assume_unique=True)]
    return bool_ind, common_ind[common_inv]

def _unpack_para(p, r):
    """inside function, not to be called from outside
    takes in parameters and unpack them"""
    # get number of levels
    l = r['c_prc']['n_levels']
    
    # unpack parameters into dict
    p_dict = {}
    p_dict['mu_0']    = p[0:l]
    p_dict['sa_0']    = p[l:2*l]
    p_dict['rho']     = p[2*l:3*l]
    p_dict['ka']      = p[3*l:4*l-1]
    p_dict['om']      = p[4*l-1:5*l-2]
    with np.errstate(divide='ignore'): p_dict['th'] = np.exp(p[5*l-2])
    # for continuus hgf
    if not 'binary' in r['c_prc']['model']:
        p_dict['pi_u']  = p[5*l-1]
        p_dict['al']    = 1/p[5*l-1]
    return(p_dict)


def _sgm(x, a):
    return(np.divide(a,1+np.exp(-x)))
