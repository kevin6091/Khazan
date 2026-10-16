"""Read current saved effect consumers, material alpha graphs and HeinMach snow."""
from pathlib import Path
import hashlib, json, os, re, traceback
import unreal as u
MAIN = Path(os.environ['KZ_ALPHA_MAIN']); OUT = Path(os.environ['KZ_ALPHA_OUT'])
PROJECT = Path(u.Paths.project_dir()).resolve()
EAL = u.EditorAssetLibrary; LIB = u.MaterialEditingLibrary
REG = u.AssetRegistryHelpers.get_asset_registry()
REG.search_all_assets(True)
R = {'status': 'running', 'scope': 'Existing saved manifests -> current animations and installed feedback; current HeinMach effect components. No Content-wide resurvey.',
     'inputs': [], 'animations': [], 'systems': [], 'materials': [], 'snow': {}, 'missing': [], 'assets_saved': False}
OUT.joinpath('Exports').mkdir(exist_ok=True)
PATHS = set()
FILES = [
    'Saved/ImportReports/PlayerAttackVFX_20261008/Authoring/CombinedPrivateAuthoring.json',
    'Saved/ImportReports/MonsterVFX_20261008/Authoring/PrivateAuthoring.json',
    'Metadata/CombatImpactUpgrade_20261012/FinalVerification.json',
    'Metadata/BeastDodge_20261012/Completion/FinalVerification.json',
    'Metadata/Parry_20261012/FinalVerification.json',
    'Metadata/PlayerSlamDistort_20261012/FinalVerification.json',
    'Metadata/CombatFinishFollowup_20261012/FinalVerification.json',
    'Metadata/MonsterBloodReference_20261012/FinalVerification.json',
]

def collect(value):
    if isinstance(value, dict):
        for k, v in value.items(): collect(k); collect(v)
    elif isinstance(value, list):
        for v in value: collect(v)
    elif isinstance(value, str):
        v = value.replace('\\', '/')
        if 'Content/' in v and v.endswith('.uasset'):
            PATHS.add('/Game/' + v.split('Content/', 1)[1][:-7])
        for p in re.findall(r'/Game/[A-Za-z0-9_/.-]+', v): PATHS.add(p.split(':', 1)[0])

def data(path):
    package = path.split('.', 1)[0]
    name = package.rsplit('/', 1)[-1]
    return REG.get_asset_by_object_path(package + '.' + name)

def export(asset):
    target = OUT / 'Exports' / (hashlib.sha256(asset.get_path_name().encode()).hexdigest()[:12] + '_' + asset.get_name() + '.t3d')
    task = u.AssetExportTask(); task.object = asset; task.filename = str(target)
    task.automated = True; task.prompt = False; task.replace_identical = True; task.exporter = u.ObjectExporterT3D()
    assert u.Exporter.run_asset_export_task(task), asset.get_path_name()
    return str(target.relative_to(OUT))

def file_sha(path):
    f = PROJECT / ('Content/' + path.split('.', 1)[0].removeprefix('/Game/') + '.uasset')
    return hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None

def prop(obj, name):
    try:
        value = obj.get_editor_property(name)
        if isinstance(value, u.Object): return value.get_path_name()
        if hasattr(value, 'export_text'): return value.export_text()
        if isinstance(value, (str, int, float, bool)) or value is None: return value
        return str(value)
    except Exception: return None

try:
    for name in FILES:
        f = MAIN / name
        if f.is_file():
            R['inputs'].append({'file': name, 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()})
            collect(json.loads(f.read_text(encoding='utf-8-sig')))
    PATHS.update(['/Game/_Art/Effects/Combat/AttackContact/PP_Combat_HitBurst',
                  '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_Parry_Success',
                  '/Game/VFX/01_ARPGEssentials/KZ_Slash',
                  '/Game/VFX/05_CursedMagic/NS_Cursed_Magic_Dash1',
                  '/Game/VFX/05_CursedMagic/NS_Cursed_Magic_Blink1'])
    systems = set()
    animations = []
    for path in sorted(PATHS):
        d = data(path)
        if not d.is_valid(): continue
        cls = str(d.asset_class_path.asset_name)
        if cls in ('ParticleSystem', 'NiagaraSystem'): systems.add(str(d.package_name))
        if cls in ('AnimSequence', 'AnimMontage'): animations.append(str(d.package_name))
    for path in sorted(set(animations)):
        a = u.load_asset(path); refs = set()
        for event in u.AnimationLibrary.get_animation_notify_events(a):
            for key in ('notify', 'notify_state_class'):
                n = event.get_editor_property(key)
                if not n: continue
                # Struct text carries nested Effect/Childs and all current PS/NS/decal pointers.
                for field in ('Effect', 'ParticleTemplate', 'NiagaraTemplate', 'DecalMaterial', 'ChildParticles'):
                    value = prop(n, field)
                    if value: refs.update(re.findall(r'/Game/[A-Za-z0-9_/.-]+', str(value)))
        for ref in refs:
            d = data(ref)
            if d.is_valid() and str(d.asset_class_path.asset_name) in ('ParticleSystem', 'NiagaraSystem'):
                systems.add(str(d.package_name))
        R['animations'].append({'path': path, 'sha256': file_sha(path), 'effect_references': sorted(refs)})
    print('ALPHA_ANIMATIONS', len(R['animations']), 'SYSTEMS', len(systems), flush=True)
    world = u.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    R['heinmach_map_sha256'] = file_sha('/Game/Maps/L_HeinMach_Environment')
    R['world_effect_components'] = []
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        for typ, field in ((u.ParticleSystemComponent, 'template'), (u.NiagaraComponent, 'asset')):
            for component in actor.get_components_by_class(typ):
                asset = component.get_asset() if typ == u.NiagaraComponent else component.get_editor_property(field)
                if asset:
                    systems.add(asset.get_path_name().split('.', 1)[0])
                    R['world_effect_components'].append({'actor': actor.get_actor_label(), 'template': asset.get_path_name(), 'auto_activate': prop(component, 'auto_activate')})
    dep = u.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=True,
                                          include_searchable_names=False, include_hard_management_references=False, include_soft_management_references=False)
    queue = list(systems); seen = set(); materials = set()
    traversable = {'ParticleSystem', 'NiagaraSystem', 'NiagaraEmitter', 'StaticMesh', 'SkeletalMesh', 'Material', 'MaterialInstanceConstant', 'MaterialFunction'}
    while queue:
        path = queue.pop()
        if path in seen: continue
        seen.add(path); d = data(path)
        if not d.is_valid(): R['missing'].append(path); continue
        cls = str(d.asset_class_path.asset_name)
        if cls in ('ParticleSystem', 'NiagaraSystem'):
            asset = u.load_asset(path)
            R['systems'].append({'path': path, 'class': cls, 'sha256': file_sha(path), 'export': export(asset)})
        if cls in ('Material', 'MaterialInstanceConstant'): materials.add(path)
        for p in REG.get_dependencies(path, dep) or []:
            s = str(p)
            if not s.startswith('/Game/'): continue
            child = data(s)
            if child.is_valid() and str(child.asset_class_path.asset_name) in traversable: queue.append(s)
    for path in sorted(materials):
        a = u.load_asset(path)
        row = {'path': path, 'class': a.get_class().get_name(), 'sha256': file_sha(path), 'export': export(a),
               'metadata': {str(k): str(v) for k, v in EAL.get_metadata_tag_values(a).items()}, 'parent': prop(a, 'parent')}
        if isinstance(a, u.Material):
            row['settings'] = {k: prop(a, k) for k in ('blend_mode', 'two_sided', 'shading_model', 'translucency_pass', 'opacity_mask_clip_value')}
            row['outputs'] = {str(p): (n.get_name() if n else None) for p in
                              (u.MaterialProperty.MP_OPACITY, u.MaterialProperty.MP_OPACITY_MASK, u.MaterialProperty.MP_REFRACTION, u.MaterialProperty.MP_EMISSIVE_COLOR)
                              for n in [LIB.get_material_property_input_node(a, p)]}
            row['nodes'] = []
            for n in LIB.get_material_expressions(a):
                row['nodes'].append({'name': n.get_name(), 'class': n.get_class().get_name(),
                                     'description': prop(n, 'description'), 'code': prop(n, 'code'),
                                     'texture': prop(n, 'texture'), 'parameter_name': prop(n, 'parameter_name'),
                                     'default_value': prop(n, 'default_value'),
                                     'inputs': [i.get_name() if i else None for i in LIB.get_inputs_for_material_expression(a, n)]})
        else:
            row['base_property_overrides'] = prop(a, 'base_property_overrides')
        R['materials'].append(row)
    snow = u.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/NS_HM_SourceSnow_TwoLayers')
    budget = snow.get_editor_property('effect_type')
    R['snow'] = {'system': snow.get_path_name(), 'sha256': file_sha(snow.get_path_name()),
                 'effect_type': budget.get_path_name(), 'budget_sha256': file_sha(budget.get_path_name()),
                 'settings': budget.get_editor_property('emitter_scalability_settings').export_text(),
                 'budget_export': export(budget)}
    R['status'] = 'passed'
except Exception:
    R['status'] = 'failed'; R['error'] = traceback.format_exc()
(OUT / 'Audit.json').write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding='utf-8')
print('ALPHA_AUDIT', R['status'], 'animations', len(R['animations']), 'systems', len(R['systems']), 'materials', len(R['materials']), flush=True)
if R['status'] != 'passed': raise RuntimeError(R['error'])
