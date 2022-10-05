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
r = hgf_fit.fitModel([],
                     stims,
                     softmax_mu3_config,
                     bayes_optimal_config, 
                     quasinewton_optim_config)