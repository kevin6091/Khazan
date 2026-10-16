"""A/B repair for transparent flash: fixed-size burst and material age envelope."""
from pathlib import Path
import hashlib,json,re,unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Metadata/HitFlashCorrection_20261012'
H={};code=(ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
exec(compile(code,'hit_flash_definitions_only','exec'),H)
plan=json.loads((OUT/'Authored.json').read_text(encoding='utf-8'))
assert not (OUT/'VisiblePulse.json').exists()
for path,key in [(plan['particle']['path'],'Flash'),(plan['blood_binding']['path'],'Blood')]:
 a=u.load_asset(path);text=H['export'](a,key+'BeforePulse.t3d')
 exports={n:p for n,p in re.findall(r'Name="([^"]+)" ExportPath="[^\']+\'([^\']+)\'"',text)}
 def resolve(p):return u.load_object(None,p if p.startswith('/') else exports[p.rsplit(':',1)[-1].rsplit('.',1)[-1]])
 for i,name in [(1,'Blue'),(14,'Purple'),(2,'Red')]:
  en='KZHitFlash'+name if key=='Blood' else 'ParticleSpriteEmitter_'+str(i)
  e=u.load_object(None,a.get_path_name()+':'+en);lod=u.load_object(None,e.get_path_name()+'.ParticleLODLevel_0')
  block=re.search(r'^   Begin Object Name="'+en+r'" .*?^   End Object',text,re.M|re.S).group(0)
  modules=[resolve(p) for p in re.findall(r'Modules\(\d+\)="[^\']+\'([^\']+)\'"',block)]
  colour=next(m for m in modules if m.get_class().get_name()=='ParticleModuleColorOverLife')
  alpha=H['new']('DistributionFloatConstant',colour,'D_VisibleAlpha')
  H['set_owned'](alpha,'Constant','1')
  H['set_owned'](colour,'AlphaOverLife','(Distribution='+H['token'](alpha)+')')
  modules=[m for m in modules if m.get_class().get_name()!='ParticleModuleSizeMultiplyLife']
  H['set_owned'](lod,'Modules','('+','.join(H['token'](m) for m in modules)+')')
 H['rebuild'](a);assert u.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
 f=ROOT/('Content/'+path.removeprefix('/Game/')+'.uasset');sha=hashlib.sha256(f.read_bytes()).hexdigest()
 if key=='Flash':plan['particle']['sha256']=sha
 else:plan['blood_binding']['after']=sha
plan['pulse_diagnostic']={'growth_module':False,'alpha_module_constant':1,'source':'isolated A/B visibility verification; presentation only'}
(OUT/'AuthoredBeforePulse.json').write_text((OUT/'Authored.json').read_text(encoding='utf-8'),encoding='utf-8')
(OUT/'Authored.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
(OUT/'VisiblePulse.json').write_text(json.dumps(plan['pulse_diagnostic'],indent=2),encoding='utf-8')
print('VISIBLE_PULSE_AUTHORED')
