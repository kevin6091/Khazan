"""Guarded private one-master renderer repair; root owns execution and RHI QA.

The cooked original graph is absent. This repairs the demonstrated opaque-alpha
misread with a disclosed RGB-density/dissolve reconstruction. Particle geometry,
timing, colors, MI/source values and the Translucent blend contract are preserved.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
PROJECT = Path(unreal.Paths.project_dir()).resolve()
BASE = MAIN / 'Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Roar02'
OUTPUT = Path(os.environ['KZ_MONSTER_VFX_ROAR02_REPAIR_OUTPUT']).resolve()
PROBE = MAIN / 'Saved/ImportReports/MonsterVFX_20261008/Roar02SavedProbe/Attempt1/Probe.json'
MASTER = '/Game/_Art/Effects/Shared/Materials/Trail/FM_WPO_Trail_A'
BEFORE = '608a0ded1cd59f72a09835b512f9deb516dd2f0f622ad0e6387c9c6e78305cf2'
SOURCE = MAIN / 'Saved/Extracted/CombatEffects_20261006/Source/BBQ/Content/_Kazan_/Art/VFX/VFX_Material/Trail/FM_WPO_Trail_A.json'
SOURCE_SHA = '62195a8b23f6540900131e551865b10b99e901e4beee31cc5b03c61f13758dc9'
MI_SOURCE = MAIN / 'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/Source/BBQ/Content/_Kazan_/Art/VFX/VFX_Material/Trail/MI/FMI_WPO_Trail_A_18.json'
MI_SOURCE_SHA = 'f3f10f97660fdf65ae36044ac14e09adc29f8759f479f4cefd0b1d8f961e5071'
HLSL = ('float density=pow(saturate(max(Mask.r,max(Mask.g,Mask.b))),OpacityPower);\n'
        'return saturate(density-Dissolve)*OpacityStrength*ParticleAlpha;')
REPORT = dict(schema='Khazan.MonsterVFX.Roar02MaterialVisualRepair.v1', status='running',
              project=str(PROJECT), pid=os.getpid(), package_saves=0, source_writes=0,
              main_asset_writes=0, selected_dependency_count=1,
              rendering_boundary='Reconstructed renderer adapter; original cooked shader topology unavailable.',
              changed_properties=['MaterialExpressionMultiply_1.A: Opa_Tex.RGB -> Emi_Tex.RGB',
                  'MaterialEditorOnlyData.Opacity: opaque Tex.A terminal -> reconstructed density terminal',
                  'Material expression array: add opacity Custom + source-named DynamicParameter',
                  'Task metadata: KZFXVisualRepairRevision and KZFXVisualRepairBoundary'],
              unchanged_contracts=['Translucent blend, Unlit shading, material domain and usage flags',
                  'All existing parameter declarations/defaults and child overrides',
                  'Particle/MI/texture bytes; particle size, timing, colors and source module fields',
                  'Existing WPO/refraction limitations; this is a targeted opacity repair'],
              hlsl=HLSL,
              source_semantics={'Opa_pow': 'parent1 / exact child18 override1.5',
                  'Opa_str': 'original parent1, source parameter reused',
                  'Opa_Dissolve': 'source parent channelA, actual Roar02 module64 DynamicParams[3]',
                  'rgb_density': 'maxRGB is an explicit reconstruction, not recovered original wiring',
                  'unbound_dissolve': 'zero identity fallback for a missing engine particle stream; original graph default unconfirmed'})
KEEP = []
LIB = unreal.MaterialEditingLibrary


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disk(project, asset):
    return project / 'Content' / (asset.removeprefix('/Game/') + '.uasset')


def export(obj, name):
    path = OUTPUT / (name + '.t3d')
    assert not path.exists()
    task = unreal.AssetExportTask()
    task.object = obj
    task.filename = str(path)
    task.exporter = unreal.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    task.replace_identical = False
    assert unreal.Exporter.run_asset_export_task(task), name
    return dict(path=str(path), sha256=sha(path))


def find(material, name, cls, parameter=None):
    obj = unreal.find_object(material, name)
    assert isinstance(obj, cls), name
    if parameter:
        assert str(obj.get_editor_property('parameter_name')) == parameter, name
    KEEP.append(obj)
    return obj


def settings(material):
    return {key: str(material.get_editor_property(key)) for key in
        ('blend_mode', 'shading_model', 'two_sided', 'material_domain', 'refraction_method',
         'used_with_particle_sprites', 'used_with_mesh_particles', 'used_with_beam_trails')}


def run():
    assert PROJECT == WORK.resolve(), 'Main authoring is prohibited'
    assert OUTPUT.is_relative_to(BASE.resolve()) and OUTPUT != BASE.resolve() and OUTPUT.is_dir()
    assert not (OUTPUT / 'Repair.json').exists(), 'Never overwrite previous repair evidence'
    assert sha(SOURCE) == SOURCE_SHA and sha(MI_SOURCE) == MI_SOURCE_SHA
    probe = json.loads(PROBE.read_text(encoding='utf-8-sig'))
    assert probe['status'] == 'passed' and probe['package_bytes_unchanged'] is True
    assert Path(probe['project']).resolve() == WORK.resolve()
    expected = probe['before']
    assert expected[MASTER] == BEFORE
    before_private = {asset: sha(disk(PROJECT, asset)) for asset in expected}
    assert before_private == expected, 'Roar02 dependencies changed since fresh saved readback'
    before_main = {asset: sha(disk(MAIN, asset)) for asset in expected if disk(MAIN, asset).is_file()}
    assert before_main[MASTER] == BEFORE, 'Current Main master differs from authorized reused baseline'
    backup = OUTPUT / 'Before/Content/_Art/Effects/Shared/Materials/Trail/FM_WPO_Trail_A.uasset'
    backup.parent.mkdir(parents=True, exist_ok=False)
    shutil.copy2(disk(PROJECT, MASTER), backup)
    assert sha(backup) == BEFORE
    REPORT.update(before_private=before_private, before_main=before_main,
        source_evidence=[dict(path=str(SOURCE), sha256=SOURCE_SHA),
                         dict(path=str(MI_SOURCE), sha256=MI_SOURCE_SHA)],
        fresh_probe=dict(path=str(PROBE), sha256=sha(PROBE)),
        source_backup_root=str(OUTPUT / 'Before'))
    material = unreal.load_asset(MASTER)
    assert isinstance(material, unreal.Material)
    KEEP.append(material)
    assert material.get_editor_property('blend_mode') == unreal.BlendMode.BLEND_TRANSLUCENT
    REPORT['settings_before'] = settings(material)
    REPORT['graph_before'] = export(material, 'ParentBefore')
    opacity_texture = find(material, 'MaterialExpressionTextureSampleParameter2D_0', unreal.MaterialExpressionTextureSampleParameter2D, 'Opa_Tex')
    emission_texture = find(material, 'MaterialExpressionTextureSampleParameter2D_2', unreal.MaterialExpressionTextureSampleParameter2D, 'Emi_Tex')
    emission_multiply = find(material, 'MaterialExpressionMultiply_1', unreal.MaterialExpressionMultiply)
    particle_color = find(material, 'MaterialExpressionParticleColor_0', unreal.MaterialExpressionParticleColor)
    opacity_power = find(material, 'MaterialExpressionScalarParameter_110', unreal.MaterialExpressionScalarParameter, 'Opa_pow')
    opacity_strength = find(material, 'MaterialExpressionScalarParameter_40', unreal.MaterialExpressionScalarParameter, 'Opa_str')
    assert opacity_power.get_editor_property('default_value') == 1.0
    assert opacity_strength.get_editor_property('default_value') == 1.0
    names = json.loads(SOURCE.read_text(encoding='utf-8-sig'))[0]['Properties']['CachedExpressionData']['DynamicParameterNames']
    assert names == ['Uoffset', 'Wpo_str', 'Dist_str', 'Opa_Dissolve']
    material.modify()
    dynamic = LIB.create_material_expression(material, unreal.MaterialExpressionDynamicParameter, -1100, 1960)
    dynamic.set_editor_property('param_names', names)
    dynamic.set_editor_property('parameter_index', 0)
    # Technical neutral dissolve when no particle stream is supplied; no gameplay tuning.
    dynamic.set_editor_property('default_value', unreal.LinearColor(0, 0, 0, 0))
    opacity = LIB.create_material_expression(material, unreal.MaterialExpressionCustom, -500, 1960)
    opacity.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    opacity.set_editor_property('description', 'Roar02 RGB mask repair: reconstructed renderer, original cooked wiring unavailable')
    pins = ['Mask', 'OpacityPower', 'OpacityStrength', 'ParticleAlpha', 'Dissolve']
    inputs = []
    for pin in pins:
        value = unreal.CustomInput()
        value.set_editor_property('input_name', pin)
        inputs.append(value)
    opacity.set_editor_property('inputs', inputs)
    opacity.set_editor_property('code', HLSL)
    KEEP.extend([dynamic, opacity])
    outputs = list(LIB.get_material_expression_output_names(dynamic))
    assert len(outputs) >= 4, outputs
    binds = [(opacity_texture, 'RGB', 'Mask'), (opacity_power, '', 'OpacityPower'),
             (opacity_strength, '', 'OpacityStrength'), (particle_color, 'A', 'ParticleAlpha'),
             (dynamic, str(outputs[3]), 'Dissolve')]
    for obj, output, pin in binds:
        assert LIB.connect_material_expressions(obj, output, opacity, pin), pin
    assert LIB.connect_material_expressions(emission_texture, 'RGB', emission_multiply, 'A')
    assert LIB.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'KZFXVisualRepairRevision', 'MonsterVFX_Roar02_RGBMask_20261010')
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'KZFXVisualRepairBoundary', REPORT['rendering_boundary'])
    LIB.recompile_material(material)
    stats = LIB.get_statistics(material)
    REPORT['statistics'] = {key: int(getattr(stats, key)) for key in
        ('num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_samplers')}
    assert REPORT['statistics']['num_pixel_shader_instructions'] > 0
    assert REPORT['statistics']['num_vertex_shader_instructions'] > 0
    REPORT['settings_after'] = settings(material)
    assert REPORT['settings_after'] == REPORT['settings_before'], 'A renderer setting changed outside the graph repair'
    REPORT['graph_after'] = export(material, 'ParentAfter')
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    REPORT['package_saves'] += 1
    after_private = {asset: sha(disk(PROJECT, asset)) for asset in expected}
    after_main = {asset: sha(disk(MAIN, asset)) for asset in before_main}
    assert after_main == before_main, 'Main changed while repairing the private master'
    assert [asset for asset in expected if after_private[asset] != before_private[asset]] == [MASTER]
    REPORT.update(after_private=after_private, after_main=after_main,
        main_unchanged=True, protected_particle_and_instance_unchanged=True,
        selected_dependencies=[dict(asset=MASTER, file='Content/_Art/Effects/Shared/Materials/Trail/FM_WPO_Trail_A.uasset',
            before_main=before_main[MASTER], before_private=BEFORE, candidate_sha256=after_private[MASTER],
            role='one reused baseline dependency added by separate visual repair revision')],
        status='passed')


try:
    run()
except Exception:
    REPORT['status'] = 'failed'
    REPORT['error'] = traceback.format_exc()
finally:
    assert OUTPUT.is_relative_to(BASE.resolve()) and OUTPUT.is_dir()
    with (OUTPUT / 'Repair.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(REPORT, ensure_ascii=False, indent=2) + '\n')
if REPORT['status'] != 'passed':
    raise RuntimeError(REPORT.get('error', 'Roar02 material repair failed'))
