"""Select constant-A sprite cards, keep opaque/mesh and Additive materials intact."""
from pathlib import Path
import hashlib, json, os, shutil
MAIN=Path(__file__).resolve().parents[2]; ROOT=MAIN/'Metadata/ParticleAlpha_20261013'
WORK=MAIN.parent.parent/'Khazan_ParticleAlphaWork_20261013/Khazan'
d=json.loads((ROOT/'TextureChannelAnalysis.json').read_text()); audit=json.loads((ROOT/'Audit02/Audit.json').read_text(encoding='utf-8'))
excluded={'M_AKCartoonCharacter','FM_MeshShockWave_02','FM_Rock','M_WorldProp'}
rows=[r for r in d['sample_alpha_constant_255_candidates'] if r['master'].rsplit('/',1)[-1] not in excluded]
default='/Game/_Art/Effects/Shared/Materials/Other/DefaultParticle'
targets=sorted({r['material'] for r in rows}|{r['master'] for r in rows}|{default})
record={'status':'planned','rows':rows,'default_particle':default,'targets':targets,'excluded_mesh_rows':[r['material'] for r in d['sample_alpha_constant_255_candidates'] if r not in rows],
        'reason':'Current sample-A=255 ignores spatial density in R. Repair exact affected instances only; default switch0 retains other instances. Untextured DefaultParticle gets a soft elliptic spatial alpha.',
        'temporary_presentation':{'edge_feather_uv':.03,'edge_softness_pixels':1.25,'untextured_ellipse_power':2},'ownership_extensions':[],'before':{}}
links=WORK/'BorrowedReadOnlyLinks';links.mkdir(exist_ok=True)
for target in targets:
    relative=Path('Content/'+target.removeprefix('/Game/')+'.uasset'); dest=WORK/relative
    if not dest.resolve().is_relative_to(WORK.resolve()):
        # Move only the owned directory junction object, never its Main contents.
        prefix=WORK
        for part in relative.parts[:-1]:
            prefix=prefix/part
            if prefix.is_dir() and not prefix.resolve().is_relative_to(WORK.resolve()):
                source=prefix.resolve(); assert source.is_relative_to(MAIN/'Content')
                assert prefix.parent.resolve().is_relative_to(WORK.resolve())
                kept=links/(prefix.name+'_'+hashlib.sha256(str(prefix).encode()).hexdigest()[:10])
                assert kept.parent.resolve().is_relative_to(WORK.resolve()) and not kept.exists()
                os.rename(prefix,kept);shutil.copytree(source,prefix)
                record['ownership_extensions'].append({'owned_folder':str(prefix.relative_to(WORK)),'read_only_junction_kept':str(kept.relative_to(WORK))})
    assert dest.resolve().is_relative_to(WORK.resolve()),str(dest)
    source=MAIN/relative; h=hashlib.sha256(source.read_bytes()).hexdigest(); assert hashlib.sha256(dest.read_bytes()).hexdigest()==h
    record['before'][relative.as_posix()]=h
    backup=ROOT/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
(ROOT/'RepairPlan.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({'material_instances':len(rows),'master_materials':len({r['master'] for r in rows})+1,'target_files':len(targets),'owned_folders_added':len(record['ownership_extensions'])}))
