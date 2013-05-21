# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""SPM wrappers for preprocessing data

   Change directory to provide relative paths for doctests
   >>> import os
   >>> filepath = os.path.dirname( os.path.realpath( __file__ ) )
   >>> datadir = os.path.realpath(os.path.join(filepath, '../../testing/data'))
   >>> os.chdir(datadir)
"""

__docformat__ = 'restructuredtext'

# Standard library imports
from copy import deepcopy
import os
from glob import glob

# Third-party imports
import numpy as np

# Local imports
from nipype.interfaces.base import (OutputMultiPath, TraitedSpec, isdefined,
                                    traits, InputMultiPath, File)
from nipype.interfaces.spm.base import (SPMCommand, scans_for_fname,
                                        func_is_3d,
                                        scans_for_fnames, SPMCommandInputSpec)
from nipype.utils.filemanip import (fname_presuffix, filename_to_list,
                                    list_to_filename, split_filename)


class RealignUnwarpInputSpec(SPMCommandInputSpec):
    in_files = traits.Either(traits.List(File(exists=True)),File(exists=True),
                             field='data.scans',
                             mandatory=True,
                             desc='list of filenames to realign/uwarp', copyfile=True)
    phase_map =  File(exists=True, field='data.pmscan',
                      desc='phase map in alignment with first session, if empty, not run')                      
    #jobtype = traits.Enum('estwrite', 'estimate', 'write',
    #                      desc='one of: estimate, write, estwrite',
    #                      usedefault=True)
    quality = traits.Range(low=0.0, high=1.0, field='eoptions.quality',
                           desc='0.1 = fast, 1.0 = precise')
    fwhm = traits.Range(low=0.0, field='eoptions.fwhm',
                        desc='gaussian smoothing kernel width')
    separation = traits.Range(low=0.0, field='eoptions.sep',
                              desc='sampling separation in mm')
    register_to_mean = traits.Bool(field='eoptions.rtm',
                desc='Indicate whether realignment is done to the mean image')
    weight_img = File(exists=True, field='eoptions.weight',
                             desc='filename of weighting image')
    interp = traits.Range(low=0, high=7, field='eoptions.einterp',
                          desc='degree of b-spline used for interpolation')
    wrap = traits.List(traits.Int(), minlen=3, maxlen=3,
                        field='eoptions.ewrap',
                        desc='Check if interpolation should wrap in [x,y,z]')
    basis_functions = traits.List(traits.Int(), minlen=2, maxlen=2,
                                  field='uweoptions.basfcn',
                                  desc='Number of basis functions for each dimension default=[12,12]')
    regularisation_order = traits.Range(low=0, high=3, field='uweoptions.regorder',
                                        desc='Weight to balance compromise between likelihood function'\
                                        'and smoothing constraint')
    jacobian_deformations = traits.Bool(field='uweoptions.jm',
                                        desc='do jacobian intensity modulation, default is False')
    first_order_effects = traits.List(traits.Int(),maxlen=6,
                                      desc = 'Vector of first order effects to model; 1=xtran,2=ytran'\
                                      '3=ztran, 4=xrot, 5=yrot, 6=zrot, (default=[4,5], pitch and roll)')
    second_order_effects = traits.List(traits.Int(),maxlen=6,
                                      desc = 'Vector of second order effects to model; 1=xtran,2=ytran'\
                                      '3=ztran, 4=xrot, 5=yrot, 6=zrot, (default=[], None)')
    uwfwhm = traits.Range(low=0.0, field='uweoptions.uwfwhm',
                        desc='smoothing for unwarp (default = 4)')
    re_estimate_move = traits.Bool(field='uweoptions.rem',
                                   desc = 're-estimate movement parameters at each unwarp (Default = True)')
    num_iterations = traits.Range(low=1, high = 10, field='uweoptions.noi',
                                  desc = 'Number of iterations, (Default = 5)')
    taylor_expansion_point = traits.Enum('Average', 'First', 'Last',
                                         desc='time point to do taylor expansion around,'\
                                         '(default=Average; should give best variance reduction')
    


                                         
    write_which = traits.Tuple(traits.Int, traits.Int, field='uwroptions.uwwhich',
                              desc='determines which images to reslice '\
                               'default = (2,1) is all images plus mean')
    write_interp = traits.Range(low=0, high=7, field='uwroptions.rinterp',
                                desc='degree of b-spline used for interpolation'\
                                '(default= 4; 4th degree bspline), 0=nearestneighbor,1=trilinear')
    write_wrap = traits.List(traits.Int(), minlen=3, maxlen=3,
                              field='uwroptions.wrap',
                             desc='default = [0,0,0], Check if interpolation should wrap in [x,y,z]')
    write_mask = traits.Bool(field='uwroptions.mask',
                             desc='True/False mask output image (Default = True) ')

    write_prefix = traits.Str(default_value='u', field='uwroptions.prefix',
                              desc='string prepended to filenames of smoothed images, (Default = "u")')

class RealignUnwarpOutputSpec(TraitedSpec):
    mean_image = File(exists=True, desc='Mean image file from the unwarp/realign')
    realigned_files = OutputMultiPath(traits.Either(traits.List(File(exists=True)),File(exists=True)),
                                      desc='Unwarped/Realigned files')
    realignment_parameters = OutputMultiPath(File(exists=True),
                    desc='Estimated translation and rotation parameters')

class RealignUnwarp(SPMCommand):
    """Use spm_realign for estimating within modality rigid body alignment
       and unwarping (an attempt to of remove movement related variance ) in a timeseries

    http://www.fil.ion.ucl.ac.uk/spm/doc/manual.pdf#page=25

    Examples
    --------

    >>> import nipype.interfaces.spm as spm
    >>> realignunwarp = spm.RealignUnwarp()
    >>> realignwarp.inputs.in_files = 'functional.nii'
    >>> realignwarp.inputs.register_to_mean = True
    >>> realignwarp.run() # doctest: +SKIP

    """

    input_spec = RealignUnwarpInputSpec
    output_spec = RealignUnwarpOutputSpec

    _jobtype = 'spatial'
    _jobname = 'realignunwarp'

    def _run_interface(self, runtime):
        """Executes the SPM function using MATLAB."""
        mscript = self._make_matlab_command(deepcopy(self._parse_inputs()))
        self.mlab.inputs.script = self.fix_mscript(mscript)
        #self.mlab.script = self.fix_mscript(mscript)
        print self.mlab.inputs.script
        results = self.mlab.run()
        runtime.returncode = results.runtime.returncode
        if self.mlab.inputs.uses_mcr:
            if 'Skipped' in results.runtime.stdout:
                self.raise_exception(runtime)
        runtime.stdout = results.runtime.stdout
        runtime.stderr = results.runtime.stderr
        #runtime.merged = results.runtime.merged
        return runtime

    def fix_mscript(self, mscript):
        """ugly hack to make work with current structue...
        need to turn data.scans data.pmscan into dict"""
        #newscript = mscript.replace('data.','data{1}.')
        newscript = mscript.replace('{1}.','.')
        newscript = newscript.replace('jobs.', 'jobs{1}.')
        newscript = newscript.replace('.spatial.', '.spm.spatial.')
        newscript = newscript.replace('\n{...\n', '\n')
        newscript = newscript.replace('\n};\n}','\n}')
        return newscript

    def _format_arg(self, opt, spec, val):
        """Convert input to appropriate format for spm
        """
        if opt == 'in_files':
            infiles =  scans_for_fnames(val,
                                        keep4d=True,
                                        separate_sessions=True)
            #return self._reformat_dict_for_savemat(dict(scans = infiles))
            return infiles
        #if opt == 'phase_map':
        #    infiles = val
        #    return self._reformat_dict_for_savemat(dict(pmscan = infiles))
        
        if opt == 'register_to_mean': # XX check if this is necessary
            return int(val)
        return val
    """
    def _parse_inputs(self):
        validate spm realign options if set to None ignore
                einputs = super(RealignUnwarp, self)._parse_inputs()
        #return [{'%s' % (self._jobtype):einputs[0]}]
        return einputs
    """
    def _list_outputs(self):
        outputs = self._outputs().get()
        if isdefined(self.inputs.in_files):
            outputs['realignment_parameters'] = []
        for imgf in self.inputs.in_files:
            if isinstance(imgf,list):
                tmp_imgf = imgf[0]
            else:
                tmp_imgf = imgf
            outputs['realignment_parameters'].append(fname_presuffix(tmp_imgf,
                                                                     prefix='rp_',
                                                                     suffix='.txt',
                                                                     use_ext=False))
            if not isinstance(imgf,list) and func_is_3d(imgf):
                break;
        #if self.inputs.jobtype == "write" or self.inputs.jobtype == "estwrite":
        if isinstance(self.inputs.in_files[0], list):
            first_image = self.inputs.in_files[0][0]
        else:
            first_image = self.inputs.in_files[0]

        outputs['mean_image'] = fname_presuffix(first_image, prefix='meanu')
        outputs['realigned_files'] = []
        # get prefix for new files, or default 'u'
        file_prefix = self.inputs.write_prefix or 'u'
        for imgf in filename_to_list(self.inputs.in_files):
            realigned_run = []
            if isinstance(imgf,list):
                for inner_imgf in filename_to_list(imgf):
                    realigned_run.append(fname_presuffix(inner_imgf, prefix=file_prefix))
            else:
                realigned_run = fname_presuffix(imgf, prefix=file_prefix)
                outputs['realigned_files'].append(realigned_run)
        return outputs


class NewSegmentInputSpec(SPMCommandInputSpec):
    channel_files = InputMultiPath(File(exists=True),
                              desc="A list of files to be segmented",
                              field='channel', copyfile=False, mandatory=True)
    channel_info = traits.Tuple(traits.Float(), traits.Float(),
                                traits.Tuple(traits.Bool, traits.Bool),
                                desc="""A tuple with the following fields:
            - bias reguralisation (0-10)
            - FWHM of Gaussian smoothness of bias
            - which maps to save (Corrected, Field) - a tuple of two boolean values""", 
            field='channel')
    tissues = traits.List(traits.Tuple(traits.Tuple(File(exists=True), traits.Int()), traits.Int(),
                                       traits.Tuple(traits.Bool, traits.Bool), traits.Tuple(traits.Bool, traits.Bool)),
                         desc="""A list of tuples (one per tissue) with the following fields:
            - tissue probability map (4D), 1-based index to frame
            - number of gaussians
            - which maps to save [Native, DARTEL] - a tuple of two boolean values
            - which maps to save [Modulated, Unmodualted] - a tuple of two boolean values""", 
            field='tissue')
    affine_regularization = traits.Enum('mni', 'eastern', 'subj', 'none', field='warp.affreg',
                      desc='mni, eastern, subj, none ')
    warping_regularization = traits.Float(field='warp.reg',
                      desc='Aproximate distance between sampling points.')
    sampling_distance = traits.Float(field='warp.samp',
                      desc='Sampling distance on data for parameter estimation')
    write_deformation_fields = traits.List(traits.Bool(), minlen=2, maxlen=2, field='warp.write',
                                           desc="Which deformation fields to write:[Inverse, Forward]")

class NewSegmentOutputSpec(TraitedSpec):
    native_class_images = traits.List(traits.List(File(exists=True)), desc='native space probability maps')
    dartel_input_images = traits.List(traits.List(File(exists=True)), desc='dartel imported class images')
    normalized_class_images = traits.List(traits.List(File(exists=True)), desc='normalized class images')
    modulated_class_images = traits.List(traits.List(File(exists=True)), desc='modulated+normalized class images')
    transformation_mat = OutputMultiPath(File(exists=True), desc='Normalization transformation')
    bias_corrected_images = OutputMultiPath(File(exists=True), desc='bias corrected images')
    bias_field_images = OutputMultiPath(File(exists=True), desc='bias field images')

class NewSegment(SPMCommand):
    """Use spm_preproc8 (New Segment) to separate structural images into different
    tissue classes. Supports multiple modalities.

    NOTE: This interface currently supports single channel input only
    
    http://www.fil.ion.ucl.ac.uk/spm/doc/manual.pdf#page=185

    Examples
    --------
    >>> import nipype.interfaces.spm as spm
    >>> seg = spm.NewSegment()
    >>> seg.inputs.channel_files = 'structural.nii'
    >>> seg.inputs.channel_info = (0.0001, 60, (True, True))
    >>> seg.run() # doctest: +SKIP

    For VBM pre-processing [http://www.fil.ion.ucl.ac.uk/~john/misc/VBMclass10.pdf],
    TPM.nii should be replaced by /path/to/spm8/toolbox/Seg/TPM.nii

    >>> seg = NewSegment()
    >>> seg.inputs.channel_files = 'structural.nii'
    >>> tissue1 = (('TPM.nii', 1), 2, (True,True), (False, False))
    >>> tissue2 = (('TPM.nii', 2), 2, (True,True), (False, False))
    >>> tissue3 = (('TPM.nii', 3), 2, (True,False), (False, False))
    >>> tissue4 = (('TPM.nii', 4), 2, (False,False), (False, False))
    >>> tissue5 = (('TPM.nii', 5), 2, (False,False), (False, False))
    >>> seg.inputs.tissues = [tissue1, tissue2, tissue3, tissue4, tissue5]
    >>> seg.run() # doctest: +SKIP

    """

    input_spec = NewSegmentInputSpec
    output_spec = NewSegmentOutputSpec
    _jobtype = 'tools'
    _jobname = 'preproc8'

    def _format_arg(self, opt, spec, val):
        """Convert input to appropriate format for spm
        """

        if opt in ['channel_files', 'channel_info']:
            # structure have to be recreated, because of some weird traits error
            new_channel = {}
            new_channel['vols'] = scans_for_fnames(self.inputs.channel_files)
            if isdefined(self.inputs.channel_info):
                info = self.inputs.channel_info
                new_channel['biasreg'] = info[0]
                new_channel['biasfwhm'] = info[1]
                new_channel['write'] = [int(info[2][0]), int(info[2][1])]
            return [new_channel]
        elif opt == 'tissues':
            new_tissues = []
            for tissue in val:
                new_tissue = {}
                new_tissue['tpm'] = np.array([','.join([tissue[0][0], str(tissue[0][1])])], dtype=object)
                new_tissue['ngaus'] = tissue[1]
                new_tissue['native'] = [int(tissue[2][0]), int(tissue[2][1])]
                new_tissue['warped'] = [int(tissue[3][0]), int(tissue[3][1])]
                new_tissues.append(new_tissue)
            return new_tissues
        elif opt == 'write_deformation_fields':
            return [int(val[0]), int(val[1])]
        elif opt == 'warping_regularization':
            return int(val)
        elif opt == 'affine_regularization':
            return val
            
            

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['native_class_images'] = []
        outputs['dartel_input_images'] = []
        outputs['normalized_class_images'] = []
        outputs['modulated_class_images'] = []
        outputs['transformation_mat'] = []
        outputs['bias_corrected_images'] = []
        outputs['bias_field_images'] = []

        n_classes = 5
        if isdefined(self.inputs.tissues):
            n_classes = len(self.inputs.tissues)
        for i in range(n_classes):
            outputs['native_class_images'].append([])
            outputs['dartel_input_images'].append([])
            outputs['normalized_class_images'].append([])
            outputs['modulated_class_images'].append([])

        for filename in self.inputs.channel_files:
            pth, base, ext = split_filename(filename)
            if isdefined(self.inputs.tissues):
                for i, tissue in enumerate(self.inputs.tissues):
                    if tissue[2][0]:
                        outputs['native_class_images'][i].append(os.path.join(pth,"c%d%s%s"%(i+1, base, ext)))
                    if tissue[2][1]:
                        outputs['dartel_input_images'][i].append(os.path.join(pth,"rc%d%s%s"%(i+1, base, ext)))
                    if tissue[3][0]:
                        outputs['normalized_class_images'][i].append(os.path.join(pth,"wc%d%s%s"%(i+1, base, ext)))
                    if tissue[3][1]:
                        outputs['modulated_class_images'][i].append(os.path.join(pth,"mwc%d%s%s"%(i+1, base, ext)))
            else:
                for i in range(n_classes):
                    outputs['native_class_images'][i].append(os.path.join(pth,"c%d%s%s"%(i+1, base, ext)))
            outputs['transformation_mat'].append(os.path.join(pth, "%s_seg8.mat" % base))
            if isdefined(self.inputs.channel_info):
                if self.inputs.channel_info[2][0]:
                    outputs['bias_corrected_images'].append(os.path.join(pth, "m%s%s" % (base, ext)))
                if self.inputs.channel_info[2][1]:
                    outputs['bias_field_images'].append(os.path.join(pth, "BiasField_%s%s" % (base, ext)))
        return outputs

class VBM8InputSpec(SPMCommandInputSpec):
    in_files = traits.Either(traits.List(File(exists=True)),File(exists=True),
                             field='estwrite.data',
                             mandatory=True,
                             desc='list of filename(s) for processing', copyfile=True)
    tpm = File(exists=True, field='estwrite.opts.tpm',
               desc='Tissue Probability Map, eg: TPM.nii')
    ngaus = traits.List(traits.Int(), minlen=6, maxlen=6, field='opts.ngaus',
                        desc='number of gaussians for each tissue class eg. [2,2,2,3,4,2]')
    
    write_gm = traits.List(traits.Int(), maxlen=4, minlen=4,
                           field='estwrite.output.GM',
                           desc='List of Grey matter write options, ' \
                           '[Int, Int, Int, Int] for [native, warped, modulated, dartel]'\
                           'native =1 or 0, warped = 1 or 0,'\
                           'modulated = 0,1,or 2 [0=none, 1=affine+nonlinear, 2 = nonlinear],'\
                           'dartel = 0,1 or 2 [0=none, 1=rigid, 2= affine]'\
                           'eg [1, 1, 2,2] would create [native, warped,nonlinear,affine]\n'
                           )
    write_wm = traits.List(traits.Int(), maxlen=4, minlen=4,
                           field='estwrite.output.WM',
                           desc='List of White matter write options, ' \
                           '[Int, Int, Int, Int] for [native, warped, modulated, dartel]'\
                           'native =1 or 0, warped = 1 or 0,'\
                           'modulated = 0,1,or 2 [0=none, 1=affine+nonlinear, 2 = nonlinear],'\
                           'dartel = 0,1 or 2 [0=none, 1=rigid, 2= affine]'\
                           'eg [True, True, 2,2] would create [native, warped,nonlinear,affine]\n'
                           )
    write_csf = traits.List(traits.Int(), maxlen=4, minlen=4,
                            field='estwrite.output.CSF',
                            desc='List of CSF  write options, ' \
                            '[Int, Int, Int, Int] for [native, warped, modulated, dartel]'\
                            'native =1 or 0, warped = 1 or 0,'\
                            'modulated = 0,1,or 2 [0=none, 1=affine+nonlinear, 2 = nonlinear],'\
                            'dartel = 0,1 or 2 [0=none, 1=rigid, 2= affine]'\
                            'eg [True, True, 2,2] would create [native, warped,nonlinear,affine]\n'
                            )
    write_bias = traits.List(traits.Bool(), traits.Bool(), traits.Bool(),
                             field='estwrite.output.bias',
                             desc='list of Bools for which bias corrected images to write'\
                             '[True/False, True/False, True/False],'\
                             'specifying [native-space, normalized, affine]')
    write_label = traits.List(traits.Bool(), traits.Bool(), traits.Bool(),
                              field = 'estwrite.output.label',
                              desc = 'list of Bools for which PVE label images to write'\
                              '[True/False, True/False, True/False],'\
                              'specifying [native-space, normalized, affine]')
    write_warps = traits.List(traits.Bool(), traits.Bool(),
                              field='estwrite.output.warps',
                              desc='Specify which warps to write'\
                              '[forward, inverse]')
    
class VBM8OutputSpec(TraitedSpec):                              
    native_class_images = traits.List(traits.List(File(exists=True)),
                                      desc='native space probability maps')
    dartel_input_images = traits.List(traits.List(File(exists=True)),
                                      desc='dartel imported class images')
    normalized_class_images = traits.List(traits.List(File(exists=True)),
                                          desc='normalized class images')
    modulated_class_images = traits.List(traits.List(File(exists=True)),
                                         desc='modulated+normalized class images')

    bias_corrected_images = traits.List(traits.List(File(exists=True)),
                                        desc='bias corrected images')
    transformation_mat = OutputMultiPath(File(exists=True), desc='Normalization transformation')
    deformation_field =  OutputMultiPath(File(exists=True), desc='Deformation field y_*')
    inverse_deformation_field = OutputMultiPath(File(exists=True), desc='Inverse Deformation field y_*')

class VBM8(SPMCommand):
    """use spm to run VBM*"""

    input_spec = VBM8InputSpec
    output_spec = VBM8OutputSpec
    _jobtype = 'tools'
    _jobname = 'vbm8'

    def _format_arg(self, opt, spec, val):
        """Convert input to appropriate format for spm
        """
        if opt in ['in_files','tpm']:
            return scans_for_fnames(val)

        if opt in ['write_gm', 'write_wm','write_csf']:
            new_tissue = {}
            new_tissue.update({'native': int(val[0])})
            new_tissue.update({'warped': int(val[1])})
            new_tissue.update({'modulated': int(val[2])})
            new_tissue.update({'dartel': int(val[3])})
            return [new_tissue]
        if opt == 'write_bias': 
            new_tissue = {}
            new_tissue.update({'native': int(val[0])})
            new_tissue.update({'warped': int(val[1])})
            new_tissue.update({'affine': int(val[2])})
            return [new_tissue]
        if opt == 'write_label':
            new_tissue = {}
            new_tissue.update({'native': int(val[0])})
            new_tissue.update({'warped': int(val[1])})
            new_tissue.update({'dartel': int(val[2])})
            return [new_tissue]
        if opt == 'write_warps':
            return [int(val[0]), int(val[1])]
        if opt == 'ngaus':
            return [int(v) for v in val]
                      
                              


    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['native_class_images'] = []
        outputs['dartel_input_images'] = []
        outputs['normalized_class_images'] = []
        outputs['modulated_class_images'] = []
        outputs['transformation_mat'] = []
        outputs['bias_corrected_images'] = []
        outputs['transformation_mat'] = []
        outputs['deformation_field'] = []
        outputs['inverse_deformation_field'] = []
        

        n_classes = 3
        for i in range(n_classes):
            outputs['native_class_images'].append([])
            outputs['dartel_input_images'].append([])
            outputs['normalized_class_images'].append([])
            outputs['modulated_class_images'].append([])
            outputs['bias_corrected_images'].append([])

        tissue_classes = [self.inputs.write_gm,self.inputs.write_wm,self.inputs.write_csf]
        for filename in self.inputs.in_files:
            pth, base, ext = split_filename(filename)
            for i, tissue in enumerate(tissue_classes):
                if isdefined(tissue):
                    if tissue[0]:
                        outputs['native_class_images'][i].append(os.path.join(pth,"p%d%s%s"%(i+1, base, ext)))
                    if tissue[1]:
                        outputs['dartel_input_images'][i].append(os.path.join(pth,"rp%d%s%s"%(i+1, base, ext)))
                    if tissue[2]:
                        outputs['normalized_class_images'][i].append(os.path.join(pth,"wrp%d%s%s"%(i+1,
                                                                                                   base, ext)))
                    if tissue[3]:
                        outputs['modulated_class_images'][i].append(os.path.join(pth,"mwrp%d%s%s"%(i+1,
                        base, ext)))
            if isdefined(self.inputs.write_bias) and any(self.inputs.write_bias):
                if self.write.bias[0]:
                    outputs['bias_corrected_images'][0].append(os.path.join(pth, "m%s%s" % (base, ext)))
                if self.write.bias[1]:
                    outputs['bias_corrected_images'][1].append(os.path.join(pth, "mr%s%s" % (base, ext)))
                if self.write.bias[2]:
                    outputs['bias_corrected_images'][1].append(os.path.join(pth, "wmr%s%s" % (base, ext)))
            outputs['transformation_mat'].append(os.path.join(pth, "%s_seg8.mat" % base))
            if isdefined(self.inputs.write_warps) and self.inputs.write_warps[0]:
                outputs['deformation_field'].append(os.path.join(pth, "y_r%s%s" % (base, ext)))
            if isdefined(self.inputs.write_warps) and self.inputs.write_warps[1]:
                outputs['inverse_deformation_field'].append(os.path.join(pth, "iy_r%s%s" % (base, ext)))    
        #return outputs

class DARTELInputSpec(SPMCommandInputSpec):
    image_files = traits.List(traits.List(File(exists=True)),
                              desc="A list of files to be segmented",
                              field='warp.images', copyfile=False, mandatory=True)
    template_prefix = traits.Str('Template', usedefault=True,
                                 field='warp.settings.template',
                                 desc='Prefix for template')
    regularization_form = traits.Enum('Linear', 'Membrane', 'Bending',
                                      field = 'warp.settings.rform',
                                      desc='Form of regularization energy term')
    iteration_parameters = traits.List(traits.Tuple(traits.Range(1,10), traits.Tuple(traits.Float, traits.Float, traits.Float),
                                                    traits.Enum(1,2,4,8,16,32,64,128,256,512),
                                                    traits.Enum(0,0.5,1,2,4,8,16,32)),
                                       minlen=6,
                                       maxlen=6,
                                       field = 'warp.settings.param',
                                       desc="""List of tuples for each iteration
                                       - Inner iterations
                                       - Regularization parameters
                                       - Time points for deformation model
                                       - smoothing parameter
                                       """)
    optimization_parameters = traits.Tuple(traits.Float, traits.Range(1,8), traits.Range(1,8),
                                           field = 'warp.settings.optim',
                                           desc="""Optimization settings a tuple
                                           - LM regularization
                                           - cycles of multigrid solver
                                           - relaxation iterations
                                           """)

class DARTELOutputSpec(TraitedSpec):
    final_template_file = File(exists=True, desc='final DARTEL template')
    template_files = traits.List(File(exists=True), desc='Templates from different stages of iteration')
    dartel_flow_fields = traits.List(File(exists=True), desc='DARTEL flow fields')

class DARTEL(SPMCommand):
    """Use spm DARTEL to create a template and flow fields

    http://www.fil.ion.ucl.ac.uk/spm/doc/manual.pdf#page=197

    Examples
    --------
    >>> import nipype.interfaces.spm as spm
    >>> dartel = spm.DARTEL()
    >>> dartel.inputs.image_files = [['rc1s1.nii','rc1s2.nii'],['rc2s1.nii', 'rc2s2.nii']]
    >>> dartel.run() # doctest: +SKIP

    """

    input_spec = DARTELInputSpec
    output_spec = DARTELOutputSpec
    _jobtype = 'tools'
    _jobname = 'dartel'

    def _format_arg(self, opt, spec, val):
        """Convert input to appropriate format for spm
        """

        if opt in ['image_files']:
            return scans_for_fnames(val, keep4d=True, separate_sessions=True)
        elif opt == 'regularization_form':
            mapper = {'Linear':0, 'Membrane':1, 'Bending':2}
            return mapper[val]
        elif opt == 'iteration_parameters':
            params = []
            for param in val:
                new_param = {}
                new_param['its'] = param[0]
                new_param['rparam'] = list(param[1])
                new_param['K'] = param[2]
                new_param['slam'] = param[3]
                params.append(new_param)
            return params
        elif opt == 'optimization parameters':
            new_param = {}
            new_param['lmreg'] = val[0]
            new_param['cyc'] = val[1]
            new_param['its'] = val[2]
            return [new_param]
        else:
            return val

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['template_files'] = []
        for i in range(6):
            outputs['template_files'].append(os.path.realpath('%s_%d.nii'%(self.inputs.template_prefix, i+1)))
        outputs['final_template_file'] = os.path.realpath('%s_6.nii'%self.inputs.template_prefix)
        outputs['dartel_flow_fields'] = []
        for filename in self.inputs.image_files[0]:
            pth, base, ext = split_filename(filename)
            outputs['dartel_flow_fields'].append(os.path.realpath(os.path.join(pth,
                                                                               'u_%s_%s%s'%(base,
                                                                                            self.inputs.template_prefix,
                                                                                            ext))))
        return outputs


class DARTELNorm2MNIInputSpec(SPMCommandInputSpec):
    template_file = File(exists=True,
                         desc="DARTEL template",
                         field='mni_norm.template', copyfile=False, mandatory=True)
    flowfield_files = InputMultiPath(File(exists=True),
                                     desc="DARTEL flow fields u_rc1*",
                                     field='mni_norm.data.subjs.flowfields',
                                     mandatory=True)
    apply_to_files = InputMultiPath(File(exists=True),
                                     desc="Files to apply the transform to",
                                     field='mni_norm.data.subjs.images',
                                     mandatory=True, copyfile=False)
    voxel_size = traits.Tuple(traits.Float, traits.Float, traits.Float,
                              desc="Voxel sizes for output file",
                              field='mni_norm.vox')
    bounding_box = traits.Tuple(traits.Float, traits.Float, traits.Float,
                                traits.Float, traits.Float, traits.Float,
                                desc="Voxel sizes for output file",
                                field='mni_norm.bb')
    modulate = traits.Bool(field='mni_norm.preserve',
                           desc="Modulate out images - no modulation preserves concentrations")
    fwhm = traits.Either(traits.Tuple(traits.Float(), traits.Float, traits.Float),
                         traits.Float(), field='mni_norm.fwhm',
                         desc='3-list of fwhm for each dimension')

class DARTELNorm2MNIOutputSpec(TraitedSpec):
    normalized_files = OutputMultiPath(File(exists=True), desc='Normalized files in MNI space')
    normalization_parameter_file = File(exists=True, desc='Transform parameters to MNI space')
class DARTELNorm2MNI(SPMCommand):
    """Use spm DARTEL to normalize data to MNI space

    http://www.fil.ion.ucl.ac.uk/spm/doc/manual.pdf#page=200

    Examples
    --------
    >>> import nipype.interfaces.spm as spm
    >>> nm = spm.DARTELNorm2MNI()
    >>> nm.inputs.template_file = 'Template_6.nii'
    >>> nm.inputs.flowfield_files = ['u_rc1s1_Template.nii', 'u_rc1s3_Template.nii']
    >>> nm.inputs.apply_to_files = ['c1s1.nii', 'c1s3.nii']
    >>> nm.inputs.modulate = True
    >>> nm.run() # doctest: +SKIP

    """

    input_spec = DARTELNorm2MNIInputSpec
    output_spec = DARTELNorm2MNIOutputSpec
    _jobtype = 'tools'
    _jobname = 'dartel'

    def _format_arg(self, opt, spec, val):
        """Convert input to appropriate format for spm
        """
        if opt in ['template_file']:
            return np.array([val], dtype=object)
        elif opt in ['flowfield_files']:
            return scans_for_fnames(val, keep4d=True)
        elif opt in ['apply_to_files']:
            return scans_for_fnames(val, keep4d=True, separate_sessions=True)
        elif opt == 'voxel_size':
            return list(val)
        elif opt == 'bounding_box':
            return list(val)
        elif opt == 'fwhm':
            if not isinstance(val, tuple):
                return [val, val, val]
            if isinstance(val, tuple):
                return val
        elif opt == 'modulate':
            return int(val)
        else:
            return val

    def _list_outputs(self):
        outputs = self._outputs().get()
        pth, base, ext = split_filename(self.inputs.template_file)
        #outputs['normalization_parameter_file'] = os.path.realpath(base+'_2mni.mat')
        outputs['normalized_files'] = []
        prefix = "w"
        if isdefined(self.inputs.modulate) and self.inputs.modulate:
            prefix = 'm' + prefix
        if isdefined(self.inputs.fwhm) and self.inputs.fwhm > 0:
            prefix = 's' + prefix
        for filename in self.inputs.apply_to_files:
            pth, base, ext = split_filename(filename)
            outputs['normalized_files'].append(os.path.realpath('%s%s%s'%(prefix,
                                                                          base,
                                                                          ext)))

        return outputs
    

if __name__ == '__main__':
    infile = glob('/home/jagust/cindeem/CODE/manja/testdata/multi2/PIDN8886_*.nii')
    infile.sort()
    startdir = os.getcwd()
    ru = RealignUnwarp(matlab_cmd = 'matlab-spm8')
    ru.inputs.in_files = infile
    
    #ru.inputs.phase_map = '/home/jagust/cindeem/CODE/manja/corgunwarp.mat'
    #mystr = ru._generate_job(contents = ru._parse_inputs()[0])
    mscript = ru._make_matlab_command(deepcopy(ru._parse_inputs()))
    print ru.fix_mscript(mscript)
    
    pth, _ = os.path.split(infile[0])
    os.chdir(pth)
    #ruout = ru.run()
    
    #os.chdir(startdir)

    vbmfile = '/home/jagust/cindeem/CODE/manja/testdata/anatomy2_vbm8/B10-235.nii'
    pth, _ = os.path.split(vbmfile)
    os.chdir(pth)
    vbm = VBM8(matlab_cmd = 'matlab-spm8')
    vbm.inputs.in_files =[vbmfile]
    vbm.inputs.write_warps = [True,True]
    vbm.inputs.write_gm = [1,1, 1,2]
    vbm.inputs.ngaus = [2,2,2,3,4,2]
    inputs = vbm._parse_inputs()
    mscript = vbm._make_matlab_command(deepcopy(inputs))
    vbmout = vbm.run()
    os.chdir(startdir)
    #print 'mfile', ruout.interface.inputs.mfile
    #print ruout.interface.mlab.inputs.script
    #spm_jobman('interactive',jobs)
