
""" run using ipy!!!
"""
import preprocess as pp
import sys
"""
this will process the  anatomicals

Run VBM on anatomicals:
-----------------------

generate native space WM, GM CSF


Run Dartel on GM, WM, CSF
-------------------------

## need to fix Dartel raises erro for not finding flowfield files
(stupid aggregate outputs bug)

select GM WM and CSF from previous

generate template and flow fields

NOTE: at UCSF they use an existing template
/data/mridata/cguo/spm8/toolbox/vbm8/Template_X_IXI550_MNI152.nii
(where X = [1-6])
ask about this
make template with notes (dated)
this will create the template we need to sue for later registration



Make skull stripped Vol
-----------------------

nipype code to generate a ss vol
(consider different threshold)

native space or affine space (check original code)

"""

if __name__ == '__main__':


    ### Change items here####
    # get structurals
    datadir = '/home/jagust/graph/data/spm_220' 
    anatomicals = pp.get_files(datadir,'B*/anat/B*_anat.nii')
    #######################################################
    # run vbm
    vbm8_dict = {}
    for anat in anatomicals:
        # copy file to processing dir
        pth, nme, ext = pp.split_filename(anat)
        subid = nme.split('_anat')[0]
        vbmdir,exists = pp.make_dir(pth, 'vbm8')
        canat = pp.copy_file(anat, vbmdir)
        if not exists: # only run if vbm directory is missing
            out = pp.spm_vbm8(canat)
        vbmd = pp.get_vbmfiles(canat)
        vbm8_dict.update({subid: vbmd})
    
    # run dartel on cohort
    
    gms = pp.get_files(datadir, '*/anat/vbm8/rp1*.nii')
    wms = pp.get_files(datadir, '*/anat/vbm8/rp2*.nii')
    gms.sort()
    wms.sort()
    files = []
    pth, nme, ext = pp.split_filename(gms[0])
    templatedir = pth
    datestr = pp.make_datestr()
    tmplt_nme = 'dartel_%s'%(datestr)
    dout = pp.spm_dartel_make(gms, wms, templatedir, tmplt_nme)
    
    template = pp.get_files(datadir,'*/anat/vbm8/%s*'%(tmplt_nme))
    
    templatedir, exists = pp.make_dir(datadir,'template')
    newtemplate = pp.copy_files(template, templatedir)
    pp.remove_files(template)
    flowfieldstmp = pp.get_files(datadir,'*/anat/vbm8/*%s*'%(tmplt_nme))
    flowfields = pp.move_flowfields(flowfieldstmp)
    dartellog = pp.write_dartel_log(newtemplate, flowfields)

    # generate skull stripped anatomicals
    for sub in sorted(vbm8_dict):
        gm = vbm8_dict[sub]['gm_native']
        wm = vbm8_dict[sub]['wm_native']
        csf = vbm8_dict[sub]['csf_native']
        anat = vbm8_dict[sub]['T1']
        ss = pp.make_skull_stripped(gm,wm,csf,anat)
        anatdir = pp.os.path.split(pp.os.path.split(anat)[0])[0]
        _ = pp.copy_file(ss,anatdir)
