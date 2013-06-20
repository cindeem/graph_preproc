from os.path import (join, split)
import sys
from glob import glob
import numpy as np


if len(sys.argv) > 1:
    txtdir = sys.argv[1]
else:
    txtdir = '/home/jagust/UCSF/Manja_Lehmann/ICN/rsfMRI_in_CONTROLS/data/NIC_3T_controls/TXTfiles'

globstr = join(txtdir, '*.txt')
alltxt = glob(globstr)
alltxt.sort()
nblocks = 1
nsubj = len(alltxt)
nnode = np.loadtxt(alltxt[0]).shape[0]
##nnode = 90
start_node = 0
end_node = nnode
node_step = 1

data = np.zeros((nblocks, nsubj, nnode, nnode))
node_slice = slice(start_node, end_node, node_step)
for s, fname in enumerate(alltxt):
    correl = np.loadtxt(fname)
    adata = np.arctanh(correl[node_slice, node_slice])
    data[0,s] = adata

outd, _ = split(txtdir)    
outf = join(outd, 'All_unmasked_data_fisher.npy')
np.save(outf, data)
