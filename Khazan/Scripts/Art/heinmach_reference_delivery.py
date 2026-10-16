"""Publish reusable evidence and verify the exact limited main installation."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/ImportReports/HeinMachReference_20261006'
STAGE=ROOT/'Saved/ArtStaging/HeinMachReference_20261006'
META=ROOT/'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachReference_20261006'
SOURCE=ROOT/'Saved/Extracted/HeinMachReference_20261006/Source'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
read=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))


def source_analysis():
    exports={};files={}
    for path in SOURCE.rglob('*.json'):
        value=read(path)
        if not isinstance(value,list):continue
        for item in value:
            if not isinstance(item,dict) or 'Properties' not in item:continue
            exports[item['Package']]=item
            files[item['Package']]={'file':str(path.relative_to(ROOT)),'sha256':sha(path)}
    assert len(exports)==13,len(exports)
    rows=[]
    for package,item in sorted(exports.items()):
        chain=[];cursor=package;seen=set();resolved={}
        while cursor in exports and cursor not in seen:
            seen.add(cursor);props=exports[cursor]['Properties'];chain.append(cursor)
            for category in ('ScalarParameterValues','VectorParameterValues','TextureParameterValues'):
                for field in props.get(category,[]) or []:
                    name=field['ParameterInfo']['Name'];key=category+'/'+name
                    if key not in resolved:
                        resolved[key]={'raw':field['ParameterValue'],'origin_package':cursor,
                                       'field':'Properties.'+category+'.'+name}
            parent=props.get('Parent')
            cursor=parent.get('ObjectPath','').rsplit('.',1)[0] if parent else ''
        props=item['Properties']
        rows.append({'package':package,'export':item['Name'],'type':item['Type'],**files[package],
                     'inheritance_chain_child_first':chain,'unresolved_parent':cursor or None,
                     'resolved_parameters':resolved,'base_property_overrides':props.get('BasePropertyOverrides'),
                     'shading_model':props.get('ShadingModel'),
                     'material_attributes':props.get('MaterialAttributes'),
                     'expression_array_present':'Expressions' in props})
    report={'source_build':'Game build number not identified. SHA256 identifies this local extraction; cached WEP build equality not proven.',
            'targeted_packages':len(exports),'full_survey':False,'rows':rows,
            'boundary':'Cooked parameters/parents/reflected graph headers, not recovered executable BRDF. BasePropertyOverrides are raw; absent overrides are not inferred here.'}
    (OUT/'SourceMaterialAnalysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    install=read(OUT/'InstallManifest.json');assert install['status']=='Applied'
    packages=[]
    for row in install['packages']:
        assert sha(ROOT/row['path'])==row['after'],row['path']
        if row['before']:assert sha(Path(install['backup'])/row['path'])==row['before']
        packages.append(row)
    audit=read(OUT/'FreshSavedSceneAudit.json');assert audit['passed'] and Path(audit['project'])==ROOT
    assert read(OUT/'main_auditProcess.json')['passed']
    capture=read(OUT/'final/Capture.json')
    assert 'error' not in capture and len(capture['views'])==5 and capture['real_game_viewport']
    images=[]
    for view in capture['views']:
        path=Path(view['image']);assert path.is_relative_to(OUT/'final') and path.is_file()
        images.append({'name':view['name'],'path':str(path.relative_to(ROOT)),'sha256':sha(path),'camera':view['camera']})
    readback=read(OUT/'particle_readback/Capture.json');assert 'error' not in readback
    geometry=readback['snow']['geometry'];flake=geometry['Source_Flakes_Fast_Large'];dust=geometry['Source_Dust']
    assert .4999<=flake['size_x_cm'][0]<=flake['size_x_cm'][1]<=.7501
    assert abs(dust['size_x_cm'][0]-.3)<.0001
    shaders=read(OUT/'ShaderVerification.json');assert len(shaders['materials'])==6
    assert all(not row['errors'] and row['instructions']>0 for row in shaders['materials'])
    motion=read(STAGE/'Saved/ImportReports/HeinMachReference_20261006/motion/MotionVerification.json')
    assert 'error' not in motion and [len(v['frames']) for v in motion['variants']]==[65]*4
    perf=read(OUT/'PerformanceVerification.json');assert len(perf['variants'])==3
    # The final five-view main capture passed before the added single-view size
    # probe. The latter reused the old process/log filename before prefix fix.
    # final/Capture.json retains five-view evidence; do not relabel its log.
    report={'passed':True,'timestamp':datetime.datetime.now().astimezone().isoformat(),
            'packages':packages,'backup_packages_verified':sum(bool(p['before']) for p in packages),
            'main_saved_scene_audit':audit['passed'],'actor_count':audit['actor_count'],
            'poses_max_delta':audit['maximum_pose_readback_delta'],'main_game_images':images,
            'main_sprite_size_readback':geometry,'shader_materials':shaders['materials'],
            'controlled_motion_frames':260,'QA_assets_installed':False,'source_shader_port':False,
            'original_visual_identity_verified':False,
            'boundary':'Verified limited main asset installation and native rendering fixes. Exact BBQ material/renderer fidelity and input-driven full gameplay remain open.'}
    (OUT/'DeliveryVerification.json').write_text(json.dumps(report,indent=2)+'\n')
    source_analysis()
    META.mkdir(parents=True,exist_ok=True)
    names=('InstallManifest','DeliveryVerification','FreshSavedSceneAudit','AppliedTrial','ShaderVerification',
           'PerformanceVerification','PerformanceCapture','ReferencePhotoAnalysis','MotionImageAnalysis','SourceMaterialAnalysis',
           'main_auditProcess','compileProcess','motionProcess','performanceProcess')
    for name in names:shutil.copy2(OUT/(name+'.json'),META/(name+'.json'))
    shutil.copy2(OUT/'final/Capture.json',META/'MainGameCapture.json')
    shutil.copy2(OUT/'particle_readback/Capture.json',META/'ParticleReadback.json')
    shutil.copy2(STAGE/'Saved/ImportReports/HeinMachReference_20261006/motion/MotionVerification.json',META/'MotionVerification.json')
    shutil.copytree(SOURCE,META/'Source',dirs_exist_ok=True)
    for name in ('WorldMaterialRequests','WorldParentRequests','WorldVariantRequests','WorldClosureRequests','TargetedPackageIndex'):
        shutil.copy2(ROOT/'Saved/Extracted/HeinMachReference_20261006'/(name+'.json'),META/(name+'.json'))
    print(json.dumps({'passed':True,'main_packages':len(packages),'backup_packages':report['backup_packages_verified'],
                      'main_game_images':len(images),'motion_frames':260,'source_metadata_packages':13,
                      'original_visual_identity_verified':False,'metadata':str(META)}))


if __name__=='__main__':main()
