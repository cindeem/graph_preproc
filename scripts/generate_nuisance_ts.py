"""
creates nuisance directory in subjects dir
splits movement params into separate EVs
renames and puts into nuisance dir
extracts WM, ventricle(CSF), and Global timeseries
and saves as evs in nuisance dir
"""


import os
import preprocess as pp
from glob import glob

if __name__ == '__main__':

    datadir = '/home/jagust/graph/data/spm_220'
    template = 'May_21_2013_14_27'
    globstr = 'B*/func/bandpass_drop5_%s/nonan*.nii.gz'%template
    
    allprocessed = glob(os.path.join(datadir, globstr))
    allprocessed.sort()
    nimgs = len(allprocessed)

    seeds = glob(os.path.join(datadir, 'seeds/*.nii.gz'))
    seeds.sort()

    for processed in allprocessed[:]:

        basepth = processed.split('/func/')[0]
        _, subid = os.path.split(basepth)
        seed_dir, _ = pp.make_dir(basepth, 'seed_ts')
        nuisance_dir, exists = pp.make_dir(seed_dir, 'nuisance')
        if exists:
            print '%s has nuisance seeds'%subid
            continue
        seeds_ts = pp.extract_seed_ts(processed, seeds)
        for seed in seeds_ts:
            outseedfile = os.path.join(nuisance_dir, seed + '.1D')
            seeds_ts[seed].tofile(outseedfile, sep='\n')
        # write movement parameters
        param_file = pp.get_files(basepth, 'func/realign_unwarp/rp*.txt*')
        mvmt_files = pp.split_movement_params(param_file[0], nuisance_dir)
        
    
                 
                              
