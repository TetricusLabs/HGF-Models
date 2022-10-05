import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import random
import seaborn as sns

from IPython.core.pylabtools import figsize

from HGF import hgf_fit
from HGF import hgf_sim

# import the presentation functions for plotting and storing
from HGF import hgf_pres

# load our configuration functions
from HGF.hgf_config import *
from HGF.hgf import *

# set trials per blocks and number of blocks
n_blocks = 5
tpb = 250

# methed of how to jitter
jitter_method = 'gaussian'   # jitter method: gaussian, or uniform, or False
jitter_amount = 1

# set probabilities of A - B
probz = [0.5, 0.125, 0.03125, 0.875, 0.96875]
stim_values = [4, 8]

# create array to sture stimuli
stims = np.empty(n_blocks * tpb)


inf_states = np.random.rand(160, 3, 5, 4)
# inf_states = np.full((160, 3, 5, 5), -1, dtype=np.int8)


r = {}

r['y'] = np.zeros((160, 1))
r['u'] = np.zeros((160, 1))
r['ign'] = np.array([])
r['irr'] = np.array([], dtype=np.int8)
r['c_prc'] = {}
# x = SimpleNamespace()
x = {}
x['predorpost'] = 1
x['model'] = 'softmax_mu3'
x['priormus'] = np.array([])
x['priorsas'] = np.array([])
r['c_obs'] = x

softmax_mu3(r, inf_states)
# (r, inf_states)


# r = hgf_fit.fitModel([],
#                      stims,
#                      softmax_mu3_config,
#                      bayes_optimal_config, 
#                      quasinewton_optim_config)