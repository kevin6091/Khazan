"""Curate outfits, retaining three face identities instead of a face product."""
import pathlib,json,runpy,re,hashlib,itertools,struct,collections
D=runpy.run_path(str(pathlib.Path(__file__).with_name('discover_enemy_expansion.py')))
ROOT=D['ROOT'];OLD=D['OLD'];PROJECT=D['PROJECT'];read=D['read'];write=D['write'];refs=D['refs']
BASE='/Game/_Art/Enemies/HeinMach';EXTRA='/Game/_Art/Enemies/OtherRegions';META=ROOT/'Metadata'
IMPORT=runpy.run_path(str(pathlib.Path(__file__).with_name('build_enemy_import_manifest.py')))
def pkg(v):return IMPORT['package'](v)
def family(p):
    if any(k in p for k in ['/EmpireMagic/']):return 'Mage'
    if any(k in p for k in ['/ESwordHArmor/','/Empire_SwordHArmor/']):return 'HeavySwordsman'
    if any(k in p for k in ['/ESwordShield/','/Empire_SwordShield_E/']):return 'EliteShield_SourceReferences'
    if any(k in p for k in ['/EmpireSwordShield/','/Empire_SwordShield/']):return 'SwordShield'
    if any(k in p for k in ['/EmpireSword3/','/EmpireSword/']):return 'Swordsman'
    if any(k in p for k in ['/EmpireBow/']):return 'Archer'
    if any(k in p for k in ['/Halberd/','/EmpireHalberd_E/']):return 'HalberdElite'
    return 'SharedSourceReferences'
def main():
    closure=read(ROOT/'SourceClosure.json');objects={p:read(META/(p+'.json')) for p in closure['packages']}
    old=read(PROJECT/'Content/_Art/Enemies/HeinMach/Metadata/EnemyImportManifest.json');oldmap={k:{r['source_package']:r for r in old[k]} for k in ['meshes','textures','materials']}
    out={'destination_root':BASE,'meshes':[],'textures':[],'materials':[],'animations':[],'composites':[],'skeletons':{},'recipes':{}}
    # Reserve reused destination names too, so a newly encountered package with
    # the same basename can never silently reuse another package's asset.
    used={r['destination'].rsplit('/',1)[1]:p for group in oldmap.values() for p,r in group.items()}
    def unique(n,p):
        if n in used and used[n]!=p:n+='_'+hashlib.sha256(p.encode()).hexdigest()[:8]
        used[n]=p;return n
    for p,os in sorted(objects.items()):
        for o in os:
            t=o['Type'];n=o['Name'];pr=o.get('Properties',{})
            if t=='SkeletalMesh':
                # Extra source faces stay in the archive. The active library
                # contains face identities 001/002/003 only.
                if '/Face/' in p and not n.endswith(('001','002','003')):continue
                if n=='C_M_Human_Adult_M':continue # recipe BaseMesh is the carrier
                source=ROOT/'Assets'/(p+'.psk');sk=pkg(pr.get('Skeleton'));carrier='EmptyMesh' in n;normal=None
                if carrier:
                    skobj=next(x for x in objects[sk] if x['Type']=='Skeleton')
                    source,normal=IMPORT['full_carrier'](source,skobj,ROOT/'Derived/Carriers'/(n+'_FullSkeleton.psk'))
                folder='Shared/Parts/'+p.split('/Model/')[-1].split('/')[0] if '/Model/' in p and '/Monster_Human/' in p else 'Shared/Equipment'
                if '/Elite/Elite_M/' in p:folder='Humanoids/HeavySwordsman/Parts'
                if '/Named/Halberd/' in p:folder='Humanoids/HalberdElite/Parts'
                if carrier:folder='Shared/PoseCarriers'
                dest=oldmap['meshes'][p]['destination'] if p in oldmap['meshes'] else BASE+'/'+folder+'/'+unique('SK_EN_'+n,p)
                row={'source_package':p,'source_file':str(source),'destination':dest,'reused':p in oldmap['meshes'],'carrier':carrier,'normalization':normal,'source_skeleton':sk,'materials':[pkg(x['Material']) for x in o['SkeletalMaterials']],'source_slot_names':[x['MaterialSlotName'] for x in o['SkeletalMaterials']],'bounds':o['ImportedBounds'],'lod_files':[str(f) for f in (ROOT/'Assets'/p).parent.glob(n+'_LOD*.psk')],'morph_targets':[x['Name'] for x in os if x['Type']=='MorphTarget']}
                out['meshes'].append(row)
                if sk not in out['skeletons'] or carrier:
                    oldsk=BASE+'/Empire/Skeletons/SKEL_EN_EmpireHuman' if '/Adult/Adult_M/' in sk else BASE+'/HalberdElite/Meshes/Skeletons/SKEL_EN_C_M_HalberdV2' if '/Named/Halberd/' in sk and n=='C_M_HalberdV2' else None
                    out['skeletons'][sk]={'destination':oldsk or BASE+'/Shared/Skeletons/'+unique('SKEL_EN_'+sk.rsplit('/',1)[1],sk),'preview_mesh':dest,'carrier':carrier}
            elif t=='Texture2D':
                out['textures'].append({'source_package':p,'source_file':str(ROOT/'Assets'/(p+'.png')),'destination':oldmap['textures'][p]['destination'] if p in oldmap['textures'] else BASE+'/Shared/Textures/'+unique('T_EN_'+n,p),'reused':p in oldmap['textures'],'properties':pr,'source_object':o})
            elif t in ['Material','MaterialInstanceConstant']:
                out['materials'].append({'source_package':p,'source_type':t,'source_object':o,'destination':BASE+'/Shared/Materials/Expansion/'+('Masters/' if t=='Material' else 'Instances/')+unique(('M_EN_' if t=='Material' else 'MI_EN_')+n,p)})
            elif t in ['AnimSequence','AnimComposite']:
                if n!=p.rsplit('/',1)[1]:continue # retain renamed secondary exports in raw archive
                f=family(p);root=EXTRA if f in ['Mage','EliteShield_SourceReferences'] else BASE
                folder='SourceSequences' if t=='AnimSequence' else 'PlaybackClips'
                r={'source_package':p,'source_skeleton':pkg(pr.get('Skeleton')),'source_file':str(ROOT/'Assets'/(p+'.psa')) if t=='AnimSequence' else None,'destination':root+'/Humanoids/'+f+'/Animations/'+folder+'/'+unique(('A_EN_SRC_' if t=='AnimSequence' else 'A_EN_PLAY_')+n,p),'properties':pr,'family':f}
                out['animations' if t=='AnimSequence' else 'composites'].append(r)
    recipes={
      'Swordsman':('CD_RD_Human_Adult_M_EmpireWounded_001','CB_EmpireSword_Early',1.2),
      'SwordShield':('CD_RD_Human_Adult_M_EmpireWoounded_SwordShield_001','CB_Empire_SwordShield',1.2),
      'Archer':('CD_RD_Human_Adult_M_EmpireBowWounded_001','CB_EmpireBow_Early',1.2),
      'HeavySwordsman':('CD_RD_Human_Elite_M_Empire_Early001','CB_Empire_SwordHArmor_Early',1.3),
      'Mage':('CD_RD_Human_Adult_M_EmpireMagic001','CB_EmpireMagic',1.1),
      'MageHard':('CD_RD_Human_Adult_M_EmpireMagic001V3','CB_EmpireMagic_Hard',1.1)}
    catalog=[];meshes={v['source_package']:v for v in out['meshes']}
    for fam,(name,cb,scale) in recipes.items():
        p=next(p for p in objects if p.endswith('/'+name));pr=next(x['Properties'] for x in objects[p] if x['Name'].startswith('Default__'))
        c=next(p for p in objects if p.endswith('/'+cb));cd=next(x['Properties'] for x in objects[c] if x['Name'].startswith('Default__'));assert cd['Scale']==scale
        out['recipes'][fam]={'source':p,'properties':pr,'source_cb':c}
        lists={role:pr[role+'PartsList'] for role in ['Head','Face','Upper','Lower'] if pr.get(role+'PartsList')}
        choices=list(itertools.product(range(len(lists['Upper'])),range(len(lists['Lower']))))
        for i,(u,l) in enumerate(choices):
            selection={'Upper':u,'Lower':l}
            if 'Head' in lists:selection['Head']=i%len(lists['Head'])
            if 'Face' in lists:selection['Face']=i%min(3,len(lists['Face'])) if fam!='Mage' else 0
            parts={role:pkg(lists[role][idx]['Mesh']) for role,idx in selection.items()}
            suffix='U%02d_L%02d'%(u+1,l+1)
            root=EXTRA if fam.startswith('Mage') else BASE
            r={'asset':root+'/Humanoids/'+fam+'/Blueprints/BP_EN_'+fam+'_'+suffix,'family':fam,'source_cb':c,'recipe':p,'parts':parts,'scale':scale,'source_scale_field':'Default__'+cb+'_C.Properties.Scale','source_skeleton':meshes[pkg(pr['BaseMesh'])]['source_skeleton'],'base_mesh':pkg(pr['BaseMesh']),'selection':selection,'face_identity':parts.get('Face','Helmet').rsplit('_',1)[-1],'selection_policy':'One representative per source upper/lower pair; three face identities rotated, no face Cartesian product','source_level':'OtherRegions_NotInHeinMachSpawn' if fam.startswith('Mage') else 'HeinMach_Spawn_Main01'}
            r['mesh_asset']=root+'/Humanoids/'+fam+'/Meshes/'+r['asset'].rsplit('/',1)[1].replace('BP_EN_','SK_EN_');catalog.append(r)
    hal=next(v for v in out['meshes'] if v['source_package'].endswith('/C_M_HalberdV2'))
    catalog.append({'asset':BASE+'/Humanoids/HalberdElite/Blueprints/BP_EN_HalberdElite','family':'HalberdElite','source_cb':next(p for p in objects if p.endswith('/CB_EmpireHalberd_E_Early')),'parts':{},'mesh_asset':hal['destination'],'source_skeleton':hal['source_skeleton'],'scale':1.0,'scale_status':'No explicit CB Scale; neutral art assembly scale, not asserted source runtime scale','source_level':'HeinMach_Spawn_Main01'})
    out['catalog']=catalog
    write(ROOT/'ImportManifest.json',out)
    print({k:len(out[k]) for k in out})
    print('SKELETONS',[(p.rsplit('/',1)[-1],v['destination']) for p,v in out['skeletons'].items()])

if __name__=='__main__':main()
