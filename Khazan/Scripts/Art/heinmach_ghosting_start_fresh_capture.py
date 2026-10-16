import runpy
variants=[dict(name='Delivered_100_AA2_Count2_SavedParts254',screen=100,aa=2,count=2,all_parts_stencil=False)]
runpy.run_path(str(OUT.parents[2]/'Scripts/Art/heinmach_ghosting_capture.py'),init_globals=dict(WORLD=WORLD,OUT=OUT,CAPTURE_VARIANTS=variants))
