"""Bake shader-equivalent snow contact samples once, then author only the private map.

Run outside UE with ``bake``. In the private compiled editor use
``-KZSnowSurfaceMode=author`` or ``-KZSnowSurfaceMode=audit``.
No runtime texture reads, main writes, material writes, or collision changes.
"""
from pathlib import Path
from array import array
import hashlib
import json
import math
import random
import struct
import sys
import time
import traceback
import zlib

MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
STAGE=Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT=MAIN/'Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008'
META=MAIN/'Content/_Art/Player/Environment/Rendering/Metadata/LookRestoration_20261002'
SETTINGS=MAIN/'Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/SavedSettings.json'
MAP=Path('Content/Maps/L_HeinMach_Environment.umap')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))

def png_gray8(path):
    """Exact source PNG bytes; do not apply sRGB/gamma conversion."""
    blob=path.read_bytes();assert blob[:8]==b'\x89PNG\r\n\x1a\n'
    offset=8;compressed=bytearray();width=height=None
    while offset<len(blob):
        size=struct.unpack_from('>I',blob,offset)[0]
        kind=blob[offset+4:offset+8];payload=blob[offset+8:offset+8+size]
        assert zlib.crc32(kind+payload)&0xffffffff==struct.unpack_from('>I',blob,offset+8+size)[0]
        if kind==b'IHDR':
            width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',payload)
            assert (depth,color,compression,filtering,interlace)==(8,0,0,0,0),(path,depth,color,interlace)
        elif kind==b'IDAT':compressed.extend(payload)
        offset+=size+12
        if kind==b'IEND':break
    raw=zlib.decompress(compressed);assert len(raw)==(width+1)*height
    result=bytearray(width*height);previous=bytearray(width)
    for y in range(height):
        mode=raw[y*(width+1)];row=bytearray(raw[y*(width+1)+1:(y+1)*(width+1)])
        assert mode in range(5)
        for x in range(width):
            left=row[x-1] if x else 0;up=previous[x];upper_left=previous[x-1] if x else 0
            if mode==1:predictor=left
            elif mode==2:predictor=up
            elif mode==3:predictor=(left+up)//2
            elif mode==4:
                p=left+up-upper_left;a=abs(p-left);b=abs(p-up);c=abs(p-upper_left)
                predictor=left if a<=b and a<=c else (up if b<=c else upper_left)
            else:predictor=0
            row[x]=(row[x]+predictor)&255
        result[y*width:(y+1)*width]=row;previous=row
    return width,height,result

def bilinear(values,width,height,u,v,channels=1):
    # GPU normalized texture coordinates: pixel centers at (i+.5)/dimension.
    x=min(max(u*width-.5,0.),width-1.);y=min(max(v*height-.5,0.),height-1.)
    x0=int(x);y0=int(y);x1=min(x0+1,width-1);y1=min(y0+1,height-1)
    fx=x-x0;fy=y-y0
    return [((values[(y0*width+x0)*channels+c]*(1-fx)+values[(y0*width+x1)*channels+c]*fx)*(1-fy)+
             (values[(y1*width+x0)*channels+c]*(1-fx)+values[(y1*width+x1)*channels+c]*fx)*fy)
            for c in range(channels)]

def bake():
    started=time.perf_counter();OUT.mkdir(parents=True,exist_ok=True)
    plans=read(META/'HeinMachTerrainPlan.json');textures=read(META/'HeinMachTerrainTextures.json')
    saved=read(SETTINGS);materials={m['asset'].split('Landscape',1)[1].split('_',1)[0]:m for m in saved['materials']}
    manifest={'success':False,'version':1,'profiles':[],
              'layout':'interleaved little-endian float32 [weighted_height_numerator_cm,total_weight_except_puddle,snow_weight]',
              'normalization':'bilinear all three raw channels before division by max(total_weight,0.00001)',
              'sampling':'source mip0, R/255, non-sRGB, clamp, GPU texel-center coordinates',
              'provenance':{'terrain_plan':{'path':str(META/'HeinMachTerrainPlan.json'),'sha256':sha(META/'HeinMachTerrainPlan.json')},
                            'terrain_textures':{'path':str(META/'HeinMachTerrainTextures.json'),'sha256':sha(META/'HeinMachTerrainTextures.json')},
                            'material_settings':{'path':str(SETTINGS),'sha256':sha(SETTINGS)}}}
    rng=random.Random(20261008);proof=[]
    for plan in plans:
        group=plan['group'];mat=materials[group.removeprefix('Landscape')];params=mat['parameters']
        width,height=plan['dimensions'];layers={l['layer_name']:l for l in plan['layers']}
        inputs=[];source=[];height_by_layer={}
        for row in plan['weight_layers']:
            name=row['material_layer_name']
            if name=='Puddle':continue
            path=Path(row['path']);w,h,data=png_gray8(path);assert (w,h)==(width,height)
            is_snow='Snow' in layers[name]['textures']['diffuse']['object_name']
            depth=params['SnowHeightCm_'+name] if is_snow else 0.
            inputs.append((name,data,depth,is_snow));height_by_layer[name]=depth
            source.append({'layer':name,'png':str(path),'png_sha256':sha(path),
                           'native_texture':textures['weights'][group+'/'+name],
                           'snow':is_snow,'height_cm':depth,
                           'height_source':('SavedSettings material scalar SnowHeightCm_'+name) if is_snow else 'Non-snow source diffuse; zero snow height'})
        samples=array('f');zero=0;max_height=0.;max_point=0;ice_point=None
        for i in range(width*height):
            total=sum(data[i] for _,data,_,_ in inputs)/255.
            snow=sum(data[i] for _,data,_,snow in inputs if snow)/255.
            numerator=sum(data[i]*depth for _,data,depth,_ in inputs)/255.
            samples.extend((numerator,total,snow))
            current=numerator/max(total,.00001)
            if current>max_height:max_height=current;max_point=i
            if snow==0:
                zero+=1
                if total>0 and ice_point is None:ice_point=i
        if sys.byteorder!='little':samples.byteswap()
        binary=OUT/(group+'_ContactSurface.f32');binary.write_bytes(samples.tobytes())
        if sys.byteorder!='little':samples.byteswap()
        root=plan['root_location'];scale=plan['root_scale'];section=plan['min_section']
        origin=[root[axis]+(section[i]-.5)*scale[axis] for i,axis in enumerate(('X','Y'))]
        uv_scale=[plan['dimensions'][i]*scale[axis] for i,axis in enumerate(('X','Y'))]
        tests=[];max_error=0.;max_mask_error=0.;naive_error=0.
        predivided=[samples[i*3]/max(samples[i*3+1],.00001) for i in range(width*height)]
        probes=[(-.05,-.05),(1.05,1.05)]+[(rng.random(),rng.random()) for _ in range(1024)]
        for u,v in probes:
            direct_total=direct_numerator=direct_snow=0.
            for _,data,depth,is_snow in inputs:
                weight=bilinear(data,width,height,u,v)[0]/255.
                direct_total+=weight;direct_numerator+=weight*depth
                if is_snow:direct_snow+=weight
            n,t,s=bilinear(samples,width,height,u,v,3)
            expected=direct_numerator/max(direct_total,.00001);actual=n/max(t,.00001)
            expected_mask=direct_snow/max(direct_total,.00001);mask=s/max(t,.00001)
            max_error=max(max_error,abs(expected-actual));max_mask_error=max(max_mask_error,abs(mask-expected_mask))
            naive_error=max(naive_error,abs(bilinear(predivided,width,height,u,v)[0]-expected))
            if len(tests)<6:tests.append({'uv':[u,v],'world_xy_cm':[origin[0]+u*uv_scale[0],origin[1]+v*uv_scale[1]],
                                        'height_direct_cm':expected,'height_profile_cm':actual,'snow_mask':mask})
        assert max_error<.0001 and max_mask_error<.00001,(group,max_error,max_mask_error)
        assert ice_point is not None and samples[ice_point*3]==0 and samples[ice_point*3+2]==0
        profiles={'group':group,'material':mat['asset'],'uv_origin_cm':origin,'uv_scale_cm':uv_scale,
                  'resolution':[width,height],'depth_reference_cm':params['HM_DepthReferenceCm_User'],
                  'rim_height_cm':params['SnowRimHeightCm_Temporary'],'samples_file':str(binary),
                  'samples_sha256':sha(binary),'samples_count':len(samples),'bytes':binary.stat().st_size,
                  'height_by_layer_cm':height_by_layer,'sources':source}
        manifest['profiles'].append(profiles)
        def point(index):
            x=index%width;y=index//width
            return {'index':[x,y],'world_xy_cm':[origin[0]+(x+.5)*uv_scale[0]/width,origin[1]+(y+.5)*uv_scale[1]/height],
                    'height_cm':samples[index*3]/max(samples[index*3+1],.00001),'snow_mask':samples[index*3+2]/max(samples[index*3+1],.00001)}
        proof.append({'group':group,'random_uv_tests':len(probes),'max_height_error_cm':max_error,
                      'max_snow_mask_error':max_mask_error,'max_naive_predivision_error_cm':naive_error,
                      'zero_snow_texels':zero,'highest_snow':point(max_point),'non_snow_rejection':point(ice_point),
                      'examples':tests})
    manifest.update(success=True,total_bytes=sum(p['bytes'] for p in manifest['profiles']),bake_seconds=time.perf_counter()-started)
    (OUT/'SurfaceProfiles.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (OUT/'SurfaceProfileProof.json').write_text(json.dumps({'success':True,'mip0_cpu_equivalence_only':True,
      'gpu_nanite_mip_and_smooth_normal_differences_unverified':True,'runtime_texture_reads':0,
      'profile_memory_mib':manifest['total_bytes']/(1024**2),'profiles':proof},indent=2),encoding='utf-8')
    print(json.dumps({'success':True,'bytes':manifest['total_bytes'],'bake_seconds':manifest['bake_seconds'],'profiles':len(proof)}))

def author(mode):
    import unreal
    project=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    assert project==STAGE,project
    assert mode in ('author','audit')
    report={'success':False,'mode':mode,'main_map_before_sha256':sha(MAIN/MAP),
            'stage_map_before_sha256':sha(STAGE/MAP),'main_writes':False,'material_writes':False}
    try:
        manifest=read(OUT/'SurfaceProfiles.json');assert manifest['success']
        editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        assert not editor.get_game_world()
        level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        assert level.load_level('/Game/Maps/L_HeinMach_Environment')
        actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        def pose(a):
            p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
            return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
        poses={a.get_path_name():pose(a) for a in actors}
        owners=[a for a in actors if isinstance(a,unreal.KZSnowDeformation)];assert len(owners)==1
        owner=owners[0];before={key:owner.get_editor_property(key) for key in
            ('foot_radius_cm','foot_contact_height_cm','foot_compression','weapon_compression','weapon_radius_cm')}
        assert abs(before['foot_radius_cm'].x-8/1.4)<.00001 and abs(before['foot_radius_cm'].y-5/1.4)<.00001
        assert before['foot_contact_height_cm']==8 and abs(before['foot_compression']-35/55)<.00001
        assert abs(before['weapon_compression']-50/55)<.00001 and before['weapon_radius_cm']==100
        rows=[];profiles=[]
        for entry in manifest['profiles']:
            material=unreal.load_asset(entry['material']);assert material
            path=MAIN/('Content/'+entry['material'].removeprefix('/Game/')+'.uasset')
            material_sha=sha(path)
            scalar={str(n.get_editor_property('parameter_name')):n.get_editor_property('default_value')
                    for n in unreal.MaterialEditingLibrary.get_material_expressions(material)
                    if isinstance(n,unreal.MaterialExpressionScalarParameter)}
            weights={str(n.get_editor_property('parameter_name')).removeprefix('Weight_'):n.get_editor_property('texture')
                     for n in unreal.MaterialEditingLibrary.get_material_expressions(material)
                     if isinstance(n,unreal.MaterialExpressionTextureSampleParameter2D) and
                     str(n.get_editor_property('parameter_name')).startswith('Weight_')}
            for source in entry['sources']:
                texture=weights[source['layer']];assert texture
                assert texture.get_path_name().split('.')[0]==source['native_texture']
                assert not texture.get_editor_property('srgb')
                assert texture.get_editor_property('address_x')==unreal.TextureAddress.TA_CLAMP
                assert texture.get_editor_property('address_y')==unreal.TextureAddress.TA_CLAMP
            for layer,height in entry['height_by_layer_cm'].items():
                if height:assert scalar['SnowHeightCm_'+layer]==height,(layer,scalar)
            assert scalar['HM_DepthReferenceCm_User']==entry['depth_reference_cm']
            assert scalar['SnowRimHeightCm_Temporary']==entry['rim_height_cm']
            data=Path(entry['samples_file']);assert sha(data)==entry['samples_sha256']
            samples=array('f');samples.frombytes(data.read_bytes())
            if sys.byteorder!='little':samples.byteswap()
            profile=unreal.KZSnowSurfaceSamples()
            for key,value in [('material',material),('uv_origin_cm',unreal.Vector2D(*entry['uv_origin_cm'])),
              ('uv_scale_cm',unreal.Vector2D(*entry['uv_scale_cm'])),('resolution',unreal.IntPoint(*entry['resolution'])),
              ('samples',list(samples)),('depth_reference_cm',entry['depth_reference_cm']),('rim_height_cm',entry['rim_height_cm'])]:
                profile.set_editor_property(key,value)
            profiles.append(profile)
            rows.append({'material':entry['material'],'samples_count':len(samples),'material_sha256':material_sha})
        if mode=='author':
            (OUT/'Before').mkdir(exist_ok=True)
            backup=OUT/'Before/L_HeinMach_Environment.umap'
            if not backup.exists():backup.write_bytes((STAGE/MAP).read_bytes())
            owner.modify();owner.set_editor_property('surface_contact_samples',profiles)
            assert level.save_current_level()
        loaded=owner.get_editor_property('surface_contact_samples');assert len(loaded)==len(profiles)
        for actual,expected,entry in zip(loaded,profiles,manifest['profiles']):
            assert actual.get_editor_property('material')==expected.get_editor_property('material')
            assert list(actual.get_editor_property('samples'))==list(expected.get_editor_property('samples'))
            for key in ('uv_origin_cm','uv_scale_cm'):
                a=actual.get_editor_property(key);b=expected.get_editor_property(key);assert a.x==b.x and a.y==b.y
            resolution=actual.get_editor_property('resolution');assert [resolution.x,resolution.y]==entry['resolution']
            assert actual.get_editor_property('depth_reference_cm')==entry['depth_reference_cm']
            assert actual.get_editor_property('rim_height_cm')==entry['rim_height_cm']
        for key,value in before.items():assert owner.get_editor_property(key)==value,(key,value)
        assert {a.get_path_name():pose(a) for a in actors}==poses,'Actor transforms changed'
        parts=[c for a in actors for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.component_has_tag('HeinMachSnowSurface')]
        assert len(parts)==46 and len(actors)==9869
        expected_materials={p['material'] for p in manifest['profiles']}
        assert all(c.get_material(0).get_path_name().split('.')[0] in expected_materials for c in parts)
        report.update(success=True,actor=owner.get_path_name(),profiles=rows,actors=len(actors),snow_surfaces=len(parts),
                      actor_transforms_preserved=len(poses),
                      stage_map_after_sha256=sha(STAGE/MAP),main_map_after_sha256=sha(MAIN/MAP))
        assert report['main_map_before_sha256']==report['main_map_after_sha256']
        for row in rows:
            p=MAIN/('Content/'+row['material'].removeprefix('/Game/')+'.uasset');assert sha(p)==row['material_sha256']
        print('KZ_HEINMACH_SNOW_SURFACE_'+mode.upper()+'_PASSED')
    except Exception:
        report['error']=traceback.format_exc();raise
    finally:
        (OUT/('SurfaceProfiles_'+mode+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')

def launch(mode):
    import os
    import shutil
    import subprocess
    assert mode in ('author','audit')
    script=STAGE/'Scripts/Engineering/heinmach_snow_contact_surface.py'
    script.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(Path(__file__),script)
    exe='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    args=[exe,str(STAGE/'Khazan.uproject'),'-nullrhi','-unattended','-nosound','-nosplash',
          '-NoSourceControl','-NoLiveCoding','-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
          '-EnablePlugins=GameFeatures,PythonScriptPlugin','-run=pythonscript','-script='+str(script),
          '-KZSnowSurfaceMode='+mode,'-abslog='+str(OUT/('SurfaceProfiles_'+mode+'.log'))]
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    p=subprocess.Popen(args,startupinfo=si,creationflags=subprocess.CREATE_NO_WINDOW,
                       env=dict(os.environ,UE_SKIP_UBT_SDK_SETUP='1',PYTHONUTF8='1'))
    (OUT/('SurfaceProfiles_'+mode+'_Launch.json')).write_text(json.dumps({'pid':p.pid,'args':args},indent=2),encoding='utf-8')
    print('SNOW_SURFACE_BACKGROUND',mode,p.pid,flush=True);p.wait()
    report=read(OUT/('SurfaceProfiles_'+mode+'.json'))
    assert p.returncode==0 and report['success'],report
    print(json.dumps({'mode':mode,'exit_code':p.returncode,'success':True}),flush=True)

if __name__=='__main__':
    try:
        import unreal
    except ImportError:
        launch(sys.argv[2]) if len(sys.argv)>2 and sys.argv[1]=='launch' else bake()
    else:
        cmd=unreal.SystemLibrary.get_command_line()
        author('audit' if '-KZSnowSurfaceMode=audit' in cmd else 'author')
