"""
use FSL to regress WM, CSF, global and movment params out of 4D ICNdata

"""
import os
import preprocess as pp
from glob import glob

def check_nvols(infile):
    cmd = 'fslnvols %s'%(infile)
    cout = pp.CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print cout.runtime.stderr
        return None
    else:
        return int(cout.runtime.stdout.strip('\n'))
    
if __name__ == '__main__':

    TR = 2.20
    nTR = 180 # (185 -5) after drop 5 vols

    # Manja cohort values
    #TR = 2.0
    #nTR = 235 # 240 with 5 frames removed
    
    datadir = '/home/jagust/graph/data/spm_220'
    #datadir = '/home/jagust/UCSF/Manja_Lehmann/ICN/data'
    template = 'bandpass_drop5_May_21_2013_14_27'
    globstr = 'B*/func/%s/nonan*.nii.gz'%template.replace('.','*')

    ###################################################
    allprocessed = pp.get_files(datadir, globstr)
    
    nuisance_name = 'residuals.feat'
    basefsf = '/home/jagust/cindeem/CODE/manja/nuisance.fsf'
    for sub in allprocessed[1:]:
        if not nTR == check_nvols(sub):
            print sub, check_nvols(sub)
            continue
        basepth = sub.split('/func/')[0]
        _, subid = os.path.split(basepth)
        nuisance_dir = os.path.join(basepth, 'seed_ts', 'nuisance')
        nuisance_outdir = os.path.join(basepth, nuisance_name)
        fsf_dict = dict(TR='%2.2f'%TR, nTR ='%d'%nTR, nuisance_dir=nuisance_dir,
                        nuisance_outdir = nuisance_outdir,
                        input_data = sub)
        # set up fsf
        newfsf_dat = pp.update_fsf(basefsf, fsf_dict)
        fsf_file = os.path.join(basepth, 'nuisance.fsf')
        with open(fsf_file, 'w+') as fid:
            fid.write(newfsf_dat)
        out = pp.CommandLine('feat_model %s'%(fsf_file.strip('.fsf'))).run()
        if not out.runtime.returncode == 0:
            print out.runtime.stderr
            continue
        mat = fsf_file.replace('.fsf', '.mat')
        minval = pp.findmin_4d(sub)
        # run film glm
        outstatsdir = os.path.join(basepth ,'stats_%s'%template) 
        out = pp.run_film(sub, mat,outstatsdir , minval)
        if not out.runtime.returncode ==0:
            print out.runtime.stderr
            continue
        
        #Demeaning residuals and ADDING 100
        resid = os.path.join(outstatsdir, 'res4d.nii.gz')
        meanresid = os.path.join(outstatsdir, 'res4d_mean.nii.gz')
        final_res = os.path.join(outstatsdir,'%s_resid.nii.gz'%(subid))
        out = pp.CommandLine('3dTstat -mean -prefix %s %s'%(meanresid,
                                                            resid)).run()
        if not out.runtime.returncode ==0:
            print out.runtime.stderr
            continue
                                                             
        out = pp.CommandLine("3dcalc -a %s -b %s -expr '(a-b)+100' -prefix %s"%(resid, meanresid, final_res)).run()
        if not out.runtime.returncode ==0:
            print out.runtime.stderr
            continue
        print 'finished %s'%subid
