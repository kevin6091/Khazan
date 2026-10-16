import runpy
variants = [
    dict(name='Baseline_87_AA2_Count4',screen=87,aa=2,count=4,all_parts_stencil=False),
    dict(name='Native_100_AA2_Count4',screen=100,aa=2,count=4,all_parts_stencil=False),
    dict(name='Native_100_AA2_Count2',screen=100,aa=2,count=2,all_parts_stencil=False),
    dict(name='Native_100_AA3_Count2',screen=100,aa=3,count=2,all_parts_stencil=False),
    dict(name='Native_100_AA2_Count2_AllParts254',screen=100,aa=2,count=2,all_parts_stencil=True),
]
runpy.run_path(str(OUT.parents[2]/'Scripts/Art/heinmach_ghosting_capture.py'),init_globals=dict(WORLD=WORLD,OUT=OUT,CAPTURE_VARIANTS=variants))
