import os
import preprocess as pp
from glob import glob

if __name__ == '__main__':

    datadir = '/home/jagust/graph/data/spm_220'
    globstr = 'B*/stats_bandpass_drop5.Dec_04_2012./B*_resid.nii.gz'
    
    allprocessed = pp.get_files(datadir, globstr)

    seeds = ['/home/jagust/graph/data/spm_220/seeds/dang_seeds/greicius-pcc.nii']
    seeds.sort()

    for processed in allprocessed:

        basepth ,subid = os.path.split(processed)
        subdir, _ = os.path.split(basepth)
        seed_dir,exists = pp.make_dir(subdir, 'seed_ts')
        seeds_ts = pp.extract_seed_ts(processed, seeds)
        for seed in seeds_ts:
            outseedfile = os.path.join(seed_dir, seed + '.txt')
            seeds_ts[seed].tofile(outseedfile, sep='\n')
    

    
                 
                              
