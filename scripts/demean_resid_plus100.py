import nibabel
from glob import glob
import numpy as np

globstr = '/home/jagust/pib_bac/ica/data/spm_189/B*/stats/res4d.nii.gz'
allresid = glob(globstr)
allresid.sort()

for resid in allresid:
    subid = resid.split('/')[-3]
    img = nibabel.load(resid)
    dat = img.get_data()
    meandat = dat.mean(3)
    repmean = np.empty(dat.shape)
    for i in range(dat.shape[-1]):
        repmean[:,:,:,i] = meandat

    outdat = dat - repmean + 100
    outfile = resid.replace('res4d', '%s_demean_res4d'%subid)
    newimg = nibabel.Nifti1Image(outdat, img.get_affine())
    newimg.to_filename(outfile)
