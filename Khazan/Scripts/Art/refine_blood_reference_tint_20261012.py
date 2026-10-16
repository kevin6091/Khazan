from pathlib import Path
import unreal,os,json,traceback
ROOT=Path(unreal.Paths.project_dir()).resolve();assert 'Khazan_GiantFallWork_20261011' in str(ROOT)
OUT=Path(os.environ['KZ_BLOOD_REFERENCE_OUT']);lib=unreal.MaterialEditingLibrary;d={'status':'running','saved':[]}
try:
    for name,values in [('M_Monster_HitBloodGround',{'BloodMaskDensity':6.,'BloodMaskPower':.4,'BloodColor':unreal.LinearColor(.012,.00025,.00075,1)}),('M_Monster_HitBloodFluid',{'BloodColor':unreal.LinearColor(.09,.001,.0025,1)})]:
        m=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/'+name);assert m
        for n in lib.get_material_expressions(m):
            if isinstance(n,(unreal.MaterialExpressionScalarParameter,unreal.MaterialExpressionVectorParameter)):
                key=str(n.get_editor_property('parameter_name'))
                if key in values:n.set_editor_property('default_value',values[key])
        lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False);d['saved'].append(m.get_path_name())
    d.update(status='passed',temporary={'ground':{'BloodMaskDensity':6,'BloodMaskPower':.4,'BloodColor_linear':[.012,.00025,.00075]},'fluid':{'BloodColor_linear':[.09,.001,.0025]}},reason='Dark contiguous ground evidence and visible deep-red clots at the reference density; no roughness/metallic rectangle')
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(OUT/'TintRevision.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
