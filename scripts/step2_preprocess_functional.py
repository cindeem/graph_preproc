import preprocess as pp
"""

NOTE FOR BETH DATA
slicetime vars are wrong when working with her 4d files

Realign unwarp
--------------

(convert 4D -> multi 3D?)
realign and unwarp fMRI sets
code checks dim and does appropriate thing

Slice timing
------------

slice timing correction on realigned/unwarped data


Coreg
-----

find skull stripped data
coreg fMRI -> ssMRI
use fmrimean -> to original T1
apply to slice timed-realign/unwarp images

Norm Dartel to MNI
------------------

find group template
find individual warp fields/bias corrected images
use dartel to move bias corrected MRI and fMRI to MNI space
template is group Template from first Daretel run
flow field u_rp1<subject>
preserve concentraions == 0
fwhm = [0,0,0] gets reset to [4,4,4]


Bandpass Filter
---------------

remove high and very low freq from fMRI
current setting is: lowf=0.0083, highf=0.15


"""
if __name__ == '__main__':
    
    ##################
    # get functionals
    ##################
    datadir = '/home/jagust/graph/data/spm_220'
    #datadir = '/home/jagust/UCSF/Manja_Lehmann/ICN/data'
    functionals = pp.get_files(datadir,'B*/func/B*_4d.nii*')
    TR = 2.2 #set to TR = None if TR in file is correct
    #templatedir = '/home/jagust/UCSF/Manja_Lehmann/ICN/data/template'
    templatedir  = '/home/jagust/graph/data/spm_220/template'
    ##### CHANGE TEMPLATE HERE!!  ############
    template_name = 'dartel_Dec_04_2012_16_58_6.nii'
    #################################################
    template = pp.os.path.join(templatedir,template_name)

    
    ruwd = {}
    for func in functionals:

        # copy file to processing dir
        pth, nme, ext = pp.split_filename(func)
        subid = nme.split('_4d')[0]
        realigndir,exists = pp.make_dir(pth, 'realign_unwarp')
        cfunc = pp.copy_file(func, realigndir)
        slicetime_vars = pp.get_slicetime_vars(cfunc, TR = TR)
        if not exists: # only run if realign_unwarp directory is missing
            
            if pp.is_4d(cfunc):
                # convert to list of 3d files
                cfuncs = pp.fsl_split4d(cfunc, subid)
                # remove 4d file
                cfuncs = [x for x in cfuncs if not 'gz' in x]
                #pp.remove_files(cfunc)
            else:
                cfuncs = cfunc
            # realign _unwarp
            mean, ruw_funcs, paramfile = pp.spm_realign_unwarp(cfuncs)
            ## QA
            pp.qa_realigned(ruw_funcs, paramfile, subid)
        else:
            mean, ruw_funcs, paramfile = pp.get_realigned_unwarped(realigndir)

        ## slice time
        # copy file to processing dir
        slicetimedir,exists = pp.make_dir(pth, 'slicetime')
        cfunc = pp.copy_files(ruw_funcs, slicetimedir)
        if not exists:
            cfuncs = pp.spm_slicetime(cfunc,
                                      matlab_cmd='matlab-spm8',
                                      stdict = slicetime_vars)
            pp.remove_files(cfunc)

        slicetimed = pp.get_slicetimed(slicetimedir)
        ## coreg
        coregdir,exists = pp.make_dir(pth, 'coreg')
        cmean = pp.copy_file(mean, coregdir)
        cslicetimed = pp.copy_files(slicetimed, coregdir)
        anatdir = pth.replace('func', 'anat')
        target = pp.get_files(anatdir, 'ss*')
        if not exists:
            
            coreg_mean,coreg_files = pp.spm_coregister(cmean, target[0],
                                                       apply_to_files = cslicetimed)
        pp.remove_files(cmean)
        pp.remove_files(cslicetimed)
        coreg_files = pp.get_coreg_files(coregdir)
        ## dartel norm
        tmp_tmplt_nme = '_'.join(template_name.split('_')[1:6])
        d2mnidir, exists = pp.make_dir(pth,
                                       'dartel_to_MNI_%s'%(tmp_tmplt_nme))
        ccoreg = pp.copy_files(coreg_files, d2mnidir)
        canat = pp.copy_file(target[0],d2mnidir)
        flowfield = pp.get_files(anatdir, 'dartel/u_rp*%s*'%tmp_tmplt_nme)
        if not exists:
            #warp anat
            normd_anat = pp.spm_dartel_to_mni([canat], flowfield[0],template)
            # warp functionals
            flowfields = flowfield * len(ccoreg)
            normd_func = pp.spm_dartel_to_mni(ccoreg, flowfields, template)
        pp.remove_files(canat)
        pp.remove_files(ccoreg)
        warped = pp.get_warpedfunc(d2mnidir)
        # bandpass filter
        bandpassdir, exists = pp.make_dir(pth, 'bandpass_%s'%(tmp_tmplt_nme))
        cwarped = pp.copy_files(warped, bandpassdir)
        if not exists:
            file4d = pp.fsl_make4d(cwarped)
            nanfile4d = pp.clean_nan(file4d)
            filtered = pp.fsl_bandpass(nanfile4d, TR)
            pp.remove_files(file4d)
            pp.remove_files(nanfile4d)
        pp.remove_files(cwarped)
