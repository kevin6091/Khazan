import json
import unreal

roots = {}
for mesh in pawn.get_components_by_class(unreal.SkeletalMeshComponent):
    for mat in mesh.get_materials():
        while isinstance(mat, unreal.MaterialInstance):
            mat = mat.get_editor_property('parent')
        if mat and mat.get_path_name() not in roots:
            row = {}
            for prop in ['blend_mode','dithered_lod_transition','has_pixel_animation','output_translucent_velocity','world_position_offset_disable_distance']:
                row[prop] = value(mat,prop)
            roots[mat.get_path_name()] = row
master = unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/M_HM_RegionalLook')
report = dict(character_roots=roots, master=value(master,'blendable_location'))
for node in unreal.MaterialEditingLibrary.get_material_expressions(master):
    if isinstance(node,unreal.MaterialExpressionCustom):
        report['hlsl']=node.get_editor_property('code')
(OUT/'MaterialProbe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
