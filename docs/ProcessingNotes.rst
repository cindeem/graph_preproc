==========================
ICN Processing Pipeline
==========================

File structure
--------------

in data directory::

  subjectid /  
	    anat /
		 <subid>_anat.nii
	    func /
		 <subid>_4d.nii.gz


step1_preprocess_anatomy.py
---------------------------

  #. Change the datadir and globstr to get correct data

  #. Run VBM on anatomicals

  #. Run Dartel on GM, WM, CSF

  #. Make skull stripped Vol

Note::
  
  You can run dartel later on different set of subjects and then use
  for the later statges of processing

   
step2_preprocess_functional.py
------------------------------

  #. Change:

     #. datadir
     #. globstr
     #. TR
     #. Template Dir / Name (based on dartel generated from anatomicals)

  #. Realign Unwarp

  #. Slice timing correction

  #. Coreg  (fMRI -> ssMRI)
   
  #. Norm Dartel to MNI
  
  #. Bandpass Filter  (low = .0083, high = .15)

dropframes_bandpass.py
----------------------

  Optional program to drop first 5 frames and fun bandpass filter

  #. specify number of frames to drop

  #. change datadir

  #. change globstr

  #. Change TR

  #. specify template dir / template name (to choose correct files)


generate_nuisance_ts.py
-----------------------

  #. change datadir, globstr (eg. B*/func/bandpass*/nonan*.nii.gz)

  #. sets up movement parameters for model

  #. pulls nuisance ROIs from data 

  #. puts in ( <subid>/func/seed_ts/nuisance )


run_nuisance.py
---------------

  #. Specify TR, number of frames (nTR)

  #. Specify datadir and globstr (eg. B*/func/bandpass*/nonan*.nii.gz)

  #. Uses Feat to generate residuals

  #. Uses AFNI to demean residuals and add 100 (better values for modelling)


Other Tools
+++++++++++

write_seedts.py
---------------

singlesubjectRSFC.py
--------------------

