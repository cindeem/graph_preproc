import preprocess as pp
"""
get warped funcs base don template name

drop N frames

bandpass filter
"""
if __name__ == '__main__':
    
    ##################
    # get functionals
    ##################
    drop_frames = 5 # number of frames to drop
    #datadir = '/home/jagust/pib_bac/ica/data/spm_189'
    datadir = '/home/jagust/graph/data/spm_220'
    functionals = pp.get_files(datadir,'B*/func/B*_4d.nii*')
    TR = 2.2 #set to TR = None if TR in file is correct
    templatedir ='/home/jagust/graph/data/spm_220/template'
    #templatedir  = '/home/jagust/pib_bac/ica/data/spm_189/template'
    ##### CHANGE TEMPLATE HERE!!  ############
    template_name = 'dartel_May_21_2013_14_27_6.nii'
    for func in functionals[:]:
        
        # copy file to processing dir
        pth, nme, ext = pp.split_filename(func)
        subid = nme.split('_4d')[0]
        tmp_tmplt_nme = '_'.join(template_name.split('_')[1:6])
        d2mnidir, exists = pp.make_dir(pth,
                                       'dartel_to_MNI_%s'%(tmp_tmplt_nme))
        warped = pp.get_warpedfunc(d2mnidir)
        warped = warped[drop_frames:]# effectively drops your N frames
        # make new bandpass dir
    
        bandpassdir, exists = pp.make_dir(pth, 'bandpass_drop%d_%s'%(drop_frames,
                                                                     tmp_tmplt_nme))
        cwarped = pp.copy_files(warped, bandpassdir)
        if not exists:
            file4d = pp.fsl_make4d(cwarped)
            nanfile4d = pp.clean_nan(file4d)
            filtered = pp.fsl_bandpass(nanfile4d, TR)
            pp.remove_files(file4d)
            pp.remove_files(nanfile4d)
        pp.remove_files(cwarped)
    
