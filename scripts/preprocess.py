"""
pseudocode
1. realign unwarp
2. slice timing
2b. NO bet MRI before coreg  -B -f 0.05 -g 0 (maybe not)
2b. NO 3dSkullStrip -input B10-235.nii -prefix ssB10-235
    NO  3dcalc -a ss+orig.HEAD -prefix zfloat.nii -datum float -expr 'a'
2b. Segment MRI T1 to get skull stripped for coreg, and for dartel (VBM)
2c. generate skull stripped MRI for coreg
3. coreg fMRI to T1
3. norm_dartel T1 (and rFMRI)
4. bandpass filter rFMRI(fsl)



subid anatomy (T1 inplane?)
      functional (resting)
      FDG   
      PIB
      RAW - 
"""

import os,sys
from glob import glob
import datetime
import nibabel
import numpy as np
import nipype.interfaces.spm as spm
import nipype.interfaces.fsl as fsl
from nipype.interfaces.base import CommandLine
from nipype.utils.filemanip import (fname_presuffix, copyfile, split_filename)
from nipy.testing import assert_equal, assert_almost_equal,\
     assert_array_equal

sys.path.insert(0, '/home/jagust/cindeem/CODE/manja')
import nipype_ext as npe
sys.path.insert(0,'/home/jagust/cindeem/CODE/ucsf')
import quick_qa as qa


def make_datestr():
    now = datetime.datetime.now()
    return now.strftime('%b_%d_%Y_%H_%S')

def get_files(dir, globstr):
    """
    uses glob to find dir/globstr
    returns sorted list
    """
    searchstr = os.path.join(dir, globstr)
    files = glob(searchstr)
    files.sort()
    return files

def spm_realign(infiles, matlab_cmd='matlab-spm8'):
    """
    runs realignment
    returns
    mean_image, realigned_files
    """
    startdir = os.getcwd()
    pth, _ = os.path.split(infiles[0])
    os.chdir(pth)
    rlgn = spm.Realign(matlab_cmd = matlab_cmd)
    rlgn.inputs.quality = 0.9
    rlgn.inputs.separation = 4
    rlgn.inputs.fwhm = 5
    rlg.inputs.register_to_mean = False
    rlgn.inputs.write_which = [2,1]
    out = rlgn.run()
    os.chdir(startdir)
    if not out.runtime.returncode == 0:
        print out.runtime.stderr
        return None, None
    else:
        return out.outputs.mean_image, out.outputs.realigned_files

def spm_realign_unwarp(infiles):
    """ uses spm to run realign_unwarp
    Returns
    -------
    mean_img = File; mean generated by unwarp/realign

    realigned_files = Files; files unwarped and realigned

    parameters = File; file holding the trans rot params
    """
    
    startdir = os.getcwd()
    pth, _ = os.path.split(infiles[0])
    os.chdir(pth)    
    ru = npe.RealignUnwarp(matlab_cmd = 'matlab-spm8')
    ru.inputs.in_files = infiles
    ruout = ru.run()
    os.chdir(startdir)
    if not ruout.runtime.returncode == 0:
        print ruout.runtime.stderr
        return None, None, None
    return ruout.outputs.mean_image, ruout.outputs.realigned_files,\
           ruout.outputs.realignment_parameters

def get_realigned_unwarped(dir):
    """ given a directory, get the processed files
    
    Returns
    -------
    mean_img = File; mean generated by unwarp/realign

    realigned_files = Files; files unwarped and realigned

    parameters = File; file holding the trans rot params

    """
    mean_img = get_files(dir, 'meanu*.nii')
    realigned_files = get_files(dir, 'u*.nii')
    parameters = get_files(dir, 'rp*.txt')
    return mean_img[0], realigned_files, parameters[0]

def qa_realigned(files, params, subid):
    """given realigned files, and movement parameters in a txt file
    and subid for file naming
    generate QA docs
    """
    startdir = os.getcwd()
    pth, _ = os.path.split(files[0])
    os.chdir(pth)   
    qa.plot_movement(params, subid)
    files_4d = fsl_make4d(files)
    nonan_4d = clean_nan(files_4d)
    qa.plot_movement(params, subid)
    qa.save_qa_img(nonan_4d)
    remove_files(files_4d)
    os.chdir(startdir)

def get_tr(hdr):
    """attempt to get TR from header"""
    TR = None
    try:
        TR = hdr.get_slice_duration()
        #print 'first'
        return TR
    
    except:
        try:
            TR = float(hdr['db_name'].item()[4:8])/1000
            #print 'second'
            return TR
        
        except:
            TR =  hdr['pixdim'][4]
            #print 'third'
    
    return TR

def get_slicetime(nslices):
    """
    If TOTAL # SLICES = EVEN, then the excitation order when interleaved
    is EVENS first, ODDS second.
    If TOTAL # SLICES = ODD, then the excitation order when interleaved is
    ODDS first, EVENS second.
    """
    if np.mod(nslices,2) == 0:
        sliceorder = np.concatenate((np.arange(2,nslices+1,2),
                                     np.arange(1,nslices+1,2)))
    else:
        sliceorder = np.concatenate((np.arange(1,nslices+1,2),
                                     np.arange(2,nslices+1,2)))
    return sliceorder
        
def get_slicetime_vars(infiles, TR=None):
    """
    uses nibabel to get slicetime variables
    """
    if hasattr('__iter__', infiles):
        img = nibabel.load(infiles[0])
    else:
        img = nibabel.load(infiles)
    hdr = img.get_header()
    if TR is None:
        TR = get_tr(hdr)
    if TR is None:
        raise RuntimeError('TR is not defined in file')
    
    shape = img.get_shape()
    nslices = shape[2]
    TA = TR - TR/nslices
    sliceorder = get_slicetime(nslices)
    return dict(nslices=nslices,
                TA = TA,
                TR = TR,
                sliceorder = sliceorder)
        
    
    
def spm_slicetime(infiles, matlab_cmd='matlab-spm8',stdict = None):
    """
    runs slice timing
    returns
    timecorrected_files
    """
    startdir = os.getcwd()
    pth, _ = os.path.split(infiles[0])
    os.chdir(pth)    
    if stdict == None:
        stdict = get_slicetime_vars(infiles)
    sliceorder = list(stdict['sliceorder'])
    st = spm.SliceTiming(matlab_cmd = matlab_cmd)
    st.inputs.in_files = infiles
    st.inputs.ref_slice = stdict['nslices'] / 2
    st.inputs.slice_order = sliceorder
    st.inputs.time_acquisition = stdict['TA']
    st.inputs.time_repetition = stdict['TR']
    st.inputs.num_slices = stdict['nslices']
    out = st.run()
    os.chdir(startdir)
    if not out.runtime.returncode == 0:
        print out.runtime.stderr
        return None
    else:
        return out.outputs.timecorrected_files

def get_slicetimed(dir):
    """ given a directory, get the processed files
    
    Returns
    -------
    mean_img = File; mean generated by unwarp/realign

    realigned_files = Files; files unwarped and realigned

    parameters = File; file holding the trans rot params

    """
    outfiles = get_files(dir, 'au*.nii')
    return outfiles

def spm_coregister(moving, target, apply_to_files=None,
                   matlab_cmd='matlab-spm8'):
    """
    runs coregistration for moving to target
    """
    startdir = os.getcwd()
    pth, _ = os.path.split(moving)
    os.chdir(pth)    
    cr = spm.Coregister(matlab_cmd = matlab_cmd)
    cr.inputs.source = moving
    cr.inputs.target = target
    if apply_to_files is not None:
        cr.inputs.apply_to_files = apply_to_files
    out = cr.run()
    os.chdir(startdir)
    if not out.runtime.returncode == 0:
        print out.runtime.stderr
        return None, None
    else:
        return out.outputs.coregistered_source,\
               out.outputs.coregistered_files

def get_coreg_files(dir):
    outfiles = get_files(dir, 'rau*.nii')
    return outfiles    

def is_4d(infile):
    """ uses nibabel to check the dimension of a file

    Returns
    -------
    bool: True if 4d file, False if 3d file, None if > 4d
    """
    shape = nibabel.load(infile).get_shape()
    if len(shape) > 4:
        return None
    if len(shape) == 3:
        return False
    if len(shape) == 4 and shape[-1] == 1:
        # 3d file with dimensionless 4th dim
        return False
    return True
    
def fsl_make4d(infiles):
    """a list of files is passed, a 4D volume will be created
    in the same directory as the original files"""
    if not hasattr(infiles, '__iter__'):
        raise IOError('expected list,not %s'%(infiles))
    startdir = os.getcwd()
    pth, nme = os.path.split(infiles[0])
    os.chdir(pth)
    merge = fsl.Merge()
    merge.inputs.in_files = infiles
    merge.inputs.dimension = 't'
    out = merge.run()
    os.chdir(startdir)
    if not out.runtime.returncode == 0:
        print out.runtime.stderr
        return None
    else:
        return out.outputs.merged_file

def fsl_split4d(infile,sid):
    """ uses fsl to split 4d file into parts
    based on sid
    """
    startdir = os.getcwd()
    pth, nme = os.path.split(infile)
    os.chdir(pth)
    im = fsl.Split()
    im.inputs.in_file = infile
    im.inputs.dimension = 't'
    im.inputs.out_base_name = sid
    im.inputs.output_type = 'NIFTI'
    out = im.run()
    os.chdir(startdir)
    if not out.runtime.returncode == 0:
        print out.runtime.stderr
        return None
    else:
        # fsl split may include input file as an output
        ## bad globbing...
        # remove it here
        outfiles = out.outputs.out_files
        outfiles = [x for x in outfiles if not x == im.inputs.in_file]
        return outfiles
    

def clean_nan(infile):
    """removes nan from file"""
    outfile = fname_presuffix(infile, prefix='nonan_')
    im = fsl.ImageMaths()
    im.inputs.in_file = infile
    im.inputs.op_string = '-nan'
    im.inputs.out_file = outfile
    out = im.run()
    if not out.runtime.returncode == 0:
        print out.runtime.stderr
        return None
    else:
        return out.outputs.out_file



def fsl_bandpass(infile, tr, lowf=0.0083, highf=0.15):
    """ use fslmaths to bandpass filter a 4d file"""
    startdir = os.getcwd()
    pth, nme = os.path.split(infile)
    os.chdir(pth)
    low_freq = 1  / lowf / 2 / tr
    high_freq = 1 / highf / 2 / tr
    im = fsl.ImageMaths()
    im.inputs.in_file = infile
    op_str = ' '.join(['-bptf',str(low_freq), str(high_freq)])
    im.inputs.op_string = op_str
    im.inputs.suffix = 'bpfilter_l%2.2f_h%2.2f'%(low_freq, high_freq)
    out = im.run()
    os.chdir(startdir)
    if not out.runtime.returncode == 0:
        print out.runtime.stderr
        return None
    else:
        return out.outputs.out_file
    
def remove_files(files):
    """removes files """
    if not hasattr(files, '__iter__'):
        cl = CommandLine('rm %s'% files)
        out = cl.run()
        if not out.runtime.returncode == 0:
            print 'failed to delete %s' % files
            print out.runtime.stderr
        return
    for f in files:
        cl = CommandLine('rm %s'% f)
        out = cl.run()
        if not out.runtime.returncode == 0:
            print 'failed to delete %s' % f
            print out.runtime.stderr


def copy_files(infiles, newdir):
    """wraps copy file to run across multiple files
    returns list"""
    newfiles = []
    for f in infiles:
        newf = copy_file(f, newdir)
        newfiles.append(newf)
    return newfiles

def copy_file(infile, newdir):
    """ copy infile to new directory
    return full path of new file
    """
    cl = CommandLine('cp %s %s'%(infile, newdir))
    out = cl.run()
    if not out.runtime.returncode == 0:
        print 'failed to copy %s' % infile
        print out.runtime.stderr
        return None
    else:
        basenme = os.path.split(infile)[1]
        newfile = os.path.join(newdir, basenme)
        return newfile

def make_dir(base_dir, dirname='fdg_nifti'):
    """ makes a new directory if it doesnt alread exist
    returns full path
    
    Parameters
    ----------
    base_dir : str
    the root directory
    dirname  : str (default pib_nifti)
    new directory name
    
    Returns
    -------
    newdir  : str
    full path of new directory
    """
    newdir = os.path.join(base_dir,dirname)
    if not os.path.isdir(base_dir):
        raise IOError('ERROR: base dir %s DOES NOT EXIST'%(base_dir))
    directory_exists = os.path.isdir(newdir)
    if not directory_exists:
        os.mkdir(newdir)
    return newdir, directory_exists

def unzip_file(infile):
    """ looks for gz  at end of file,
    unzips and returns unzipped filename"""
    base, ext = os.path.splitext(infile)
    if not ext == '.gz':
        return infile
    else:
        cmd = CommandLine('gunzip %s' % infile)
        cout = cmd.run()
        if not cout.runtime.returncode == 0:
            print 'Failed to unzip %s'%(infile)
            return None
        else:
            return base


def move_flowfields(inflowfields):
    flowfields = []
    for ff in inflowfields:    
        pth, nme, ext = split_filename(ff)
        subdir, _ = os.path.split(pth)
        darteldir,exists = make_dir(subdir, dirname='dartel')
        newff = copy_file(ff, darteldir)
        remove_files([ff])
        flowfields.append(newff)
    return flowfields

def write_dartel_log(templates, flowfields):
    """write a log to describe template"""
    pth, nme, ext = split_filename(templates[0])
    logfile = os.path.join(pth, nme + '.log')
    with open(logfile, 'w+') as fid:
        for t in templates:
            fid.write(t + '\n')
        fid.write('\n')
        for ff in flowfields:
            fid.write(ff + '\n')
    return logfile

def spm_newsegment(infile):

    startdir = os.getcwd()
    pth, _ = os.path.split(infile)
    os.chdir(pth)    
    tpmfile = '/usr/local/matlab-tools/spm/spm8_r4010/toolbox/Seg/TPM.nii'
    ns = npe.NewSegment(matlab_cmd = 'matlab-spm8')
    ns.inputs.channel_files = [infile]
    ns.inputs.write_deformation_fields = [True, True]
    ns.inputs.tissues = [((tpmfile,1),2,(True,True),(True,True)),
                         ((tpmfile,2),2,(True,True),(True,True)),
                         ((tpmfile,3),2,(True,True),(True,True))]
    ns.inputs.warping_regularization = 4
    ns.inputs.affine_regularization = 'mni'

    nsout = ns.run()
    os.chdir(startdir)
                         


def spm_vbm8(infile):
    startdir = os.getcwd()
    pth, _ = os.path.split(infile)
    os.chdir(pth)
    vbm = npe.VBM8(matlab_cmd = 'matlab-spm8')
    vbm.inputs.in_files =[infile]
    vbm.inputs.write_warps = [True,True]
    vbm.inputs.write_gm = [1,0, 0,2] #write native, dartel afffine
    vbm.inputs.write_wm = [1,0, 0,2] #write native, dartel afffine
    vbm.inputs.write_csf = [1,0, 0,2] #write native, dartel afffine
    #vbm.inputs.write_bias = [1,0,0,2]
    vbmout = vbm.run()
    os.chdir(startdir)
    return vbmout

def spm_vbm8_rigid(infile):
    startdir = os.getcwd()
    pth, _ = os.path.split(infile)
    os.chdir(pth)
    vbm = npe.VBM8(matlab_cmd = 'matlab-spm8')
    vbm.inputs.in_files =[infile]
    vbm.inputs.write_warps = [True,True]
    vbm.inputs.write_gm = [1,0, 0,1] #write native, dartel rigid
    vbm.inputs.write_wm = [1,0, 0,1] #write native, dartel rigid
    vbm.inputs.write_csf = [1,0, 0,1] #write native, dartel rigid
    #vbm.inputs.write_bias = [True, True, True]
    vbmout = vbm.run()
    os.chdir(startdir)
    return vbmout
   

def get_vbmfiles(infile):
    """given the original T1  vbm was run on...
    find the expected output files as a dict
    T1
    gm_native
    wm_native
    csf_native
    gm_dartel
    wm_dartel
    icv_file
    icv (from *_seg8.txt
    """
    outdict = dict(T1=None,
                   gm_native = None,
                   wm_native = None,
                   csf_native = None,
                   gm_dartel = None,
                   wm_dartel = None,
                   icv_file = None,
                   icv = None)
    outdict['T1'] = infile
    outdict['gm_native'] = fname_presuffix(infile, prefix='p1')
    outdict['gm_dartel'] = fname_presuffix(infile, prefix='rp1', suffix = '_affine')
    outdict['wm_native'] = fname_presuffix(infile, prefix='p2')
    outdict['wm_dartel'] = fname_presuffix(infile, prefix='rp2', suffix = '_affine')
    outdict['csf_native'] = fname_presuffix(infile, prefix='p3')
    outdict['icv_file'] = fname_presuffix(infile, prefix='p', suffix='_seg8.txt',use_ext=False)
    #check for existence
    for item in [x for x in outdict if not outdict[x]==None]:
        if not os.path.isfile(outdict[item]):
            print item, outdict[item], ' was NOT generated/found'
            outdict[item] = None
    if outdict['icv_file'] is not None:
        outdict['icv'] = np.loadtxt(outdict['icv_file']).sum()
    return outdict

def spm_dartel_make(gm, wm, template_dir, template_nme):
    """ run dartel to make template and flowfields
    template_dir will be location of saved templates
    template_nme will be used to name template and
    flow fields"""
    startdir = os.getcwd()
    os.chdir(template_dir)
    dartel = npe.DARTEL(matlab_cmd = 'matlab-spm8')
    dartel.inputs.image_files = [gm, wm]
    dartel.inputs.template_prefix = template_nme
    dartel_out = dartel.run()
    os.chdir(startdir)
    return dartel_out



def make_skull_stripped(gm, wm, csf, vol):
    """ use nibabel to make ss vol"""
    volimg = nibabel.load(vol)
    gmdat = nibabel.load(gm).get_data()
    wmdat = nibabel.load(wm).get_data()
    csfdat = nibabel.load(csf).get_data()
    assert gmdat.shape == wmdat.shape == csfdat.shape == volimg.get_shape()
    mask = gmdat + wmdat + csfdat
    newdat = np.zeros(gmdat.shape)
    newdat[mask>0]  = volimg.get_data()[mask>0]
    newfile = fname_presuffix(vol, prefix='ss_')
    newimg = nibabel.Nifti1Image(newdat, volimg.get_affine())
    newimg.to_filename(newfile)
    return newfile


def spm_dartel_to_mni(infiles, flowfields, template):
    """ use spm to warp functionals to MNI space
    """
    work_dir, _ = os.path.split(infiles[0])
    startdir = os.getcwd()
    os.chdir(work_dir)
    d2mni = npe.DARTELNorm2MNI(matlab_cmd = 'matlab-spm8')
    d2mni.inputs.apply_to_files = infiles
    d2mni.inputs.flowfield_files = flowfields
    d2mni.inputs.template_file = template
    d2mni.inputs.fwhm = 4
    d2mni.inputs.voxel_size = (2,2,2)
    d2mni.inputs.bounding_box = (-78, -112, -70, 78, 76, 86)
    out = d2mni.run()
    os.chdir(startdir)
    if not out.runtime.returncode == 0:
        print out.runtime.stderr
        return None
    return out.outputs.normalized_files
    
def get_warpedfunc(dir):
    outfiles = get_files(dir, 'swrau*.nii')
    return outfiles    
    

def get_seedname(seedfile):
    _, nme, _ = split_filename(seedfile)
    return nme
    
def extract_seed_ts(data, seeds):
    """ check shape match of data and seed
    if same assume registration
    extract mean of data in seed > 0"""
    data_dat = nibabel.load(data).get_data()
    meants = {}
    for seed in seeds:
        seednme = get_seedname(seed)
        seed_dat = nibabel.load(seed).get_data().squeeze()
        assert seed_dat.shape == data_dat.shape[:3]
        seed_dat[data_dat[:,:,:,0].squeeze() <=0] = 0
        tmp = data_dat[seed_dat > 0,:]
        meants.update({seednme:tmp.mean(0)})
    return meants 

def split_movement_params(infile, outdir):
    """splits movement params into pitch/roll/yaw/dxLR/dxAP/dxIS
    and saves to outdir as: mc1.1D, -> mc6.1D
    """
    # gunzip file if necessary
    outfiles = []
    infile = unzip_file(infile)
    dat = np.loadtxt(infile)
    for val, tmpdat in enumerate(dat.T):
        outfile = os.path.join(outdir, 'mc%d.1D'%(val+1))
        tmpdat.tofile(outfile, sep='\n')
        outfiles.append(outfile)
    return outfiles

def update_fsf(fsf, fsf_dict):
    original = open(fsf).read()
    tmp1 = original.replace('nuisance_dir',
                            fsf_dict['nuisance_dir'])
    tmp2 = tmp1.replace('nuisance_model_outputdir',
                        fsf_dict['nuisance_outdir'])
    tmp3 = tmp2.replace('nuisance_model_input_data',
                        fsf_dict['input_data'])
    tmp4 = tmp3.replace('nuisance_model_TR',
                        fsf_dict['TR'])
    tmp5 = tmp4.replace('nuisance_model_numTRs',
                        fsf_dict['nTR'])
    return tmp5

def findmin_4d(infile):
    """finds min value of 4d data masked by self
    """
    dat = nibabel.load(infile).get_data()
    return dat[dat>0].min()

def run_film(data, mat, outdir, minval):
    cmd = 'film_gls -rn %s -noest -sa -ms 5 %s %s %d'%(outdir,
                                                       data,
                                                       mat, minval)
    out = CommandLine(cmd).run()
    return out

def demean_add100(infile):
    img = nibabel.load(infile)
    aff = img.get_affine()
    dat = img.get_data()
    newdat = dat
    
if __name__ == '__main__':

    rootdir = '/home/jagust/cindeem/CODE/manja/testdata'
    infile = os.path.join(rootdir,'resting/B08-247_resting.nii.gz')

    d = get_slicetime_vars(infile)
    assert_almost_equal( d['TA'] , 1.8112499999999998)
    assert_almost_equal( d['TR'] , 1.8899999999999999)
    assert_equal(d['nslices'], 24)
    assert_array_equal(d['sliceorder'],
                       np.concatenate((np.arange(2,25,2),
                                     np.arange(1,25,2))))
    
    # test splitting movement_params
    infile = os.path.join(rootdir, 'movement/rp_B05-2010000.txt')
    outdir, exists = make_dir(rootdir + '/movement', dirname='nuisance')
    assert_equal(exists, True)
    newfiles = split_movement_params(infile, outdir)
    tmp = np.loadtxt(newfiles[0])
    expected_data = np.array([ 0.,  0.00878314,  0.00027707, -0.00278364,
                               -0.00659256, -0.02603804, -0.04524383,
                               -0.02203125, -0.0388689 , -0.02098652])
    assert_almost_equal(tmp[:10], expected_data)
    
    
    