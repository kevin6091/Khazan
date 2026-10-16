"""Read-only native asset/socket diagnosis for the imported grab warning."""
from pathlib import Path
import json
import traceback
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / "Metadata/GiantGrabWarning_20261014"
R = {"status": "running", "monsters": [], "particle": {}, "errors": []}
try:
    R["fx_methods"] = [n for n in dir(u.FXConverterUtilitiesLibrary) if "lod_level" in n.lower() or "module" in n.lower()]
    for family in ("ApesStoneHandElite", "Yetuga"):
        cls = u.load_class(None, "/Game/Bluprints/Monsters/BP_Monster_" + family + ".BP_Monster_" + family + "_C")
        assert cls, family
        monster = u.get_default_object(cls)
        mesh = monster.get_editor_property("mesh")
        R["monsters"].append({"family": family, "mesh": mesh.get_editor_property("skeletal_mesh_asset").get_path_name(),
                              "ui_chest": mesh.does_socket_exist("UI_Chest"),
                              "spine2": mesh.does_socket_exist("Bip001-Spine2"),
                              "head": mesh.does_socket_exist("Bip001-Head"),
                              "scale": str(mesh.get_editor_property("relative_scale3d"))})
    ps = u.load_asset("/Game/_Art/Effects/Combat/GrabWarning/FP_UI_BurstAttact_Grab")
    assert ps
    emitters = u.FXConverterUtilitiesLibrary.get_cascade_system_emitters(ps)
    R["particle"] = {"path": ps.get_path_name(), "emitters": len(emitters), "names": [str(e.get_editor_property("emitter_name")) for e in emitters],
                     "required_materials": [], "emitter_details": []}
    for emitter in emitters:
        lod = u.FXConverterUtilitiesLibrary.get_cascade_emitter_lod_level(emitter, 0)
        required = u.FXConverterUtilitiesLibrary.get_lod_level_required_module(lod)
        R["particle"]["required_materials"].append(required.get_editor_property("material").get_path_name())
        detail = {"name": str(emitter.get_editor_property("emitter_name")), "type_data": None,
                  "mesh_material_overrides": [], "colors": []}
        type_data = u.FXConverterUtilitiesLibrary.get_lod_level_type_data_module(lod)
        if isinstance(type_data, u.ParticleModuleTypeDataMesh):
            props = u.FXConverterUtilitiesLibrary.get_particle_module_type_data_mesh_props(type_data)
            detail["type_data"] = {"mesh": props[0].get_path_name() if props[0] else None,
                                   "override_material": props[6]}
        for module in u.FXConverterUtilitiesLibrary.get_lod_level_modules(lod):
            if isinstance(module, u.ParticleModuleMeshMaterial):
                detail["mesh_material_overrides"] = [m.get_path_name() if m else None for m in
                                                     u.FXConverterUtilitiesLibrary.get_particle_module_mesh_material_props(module)]
            if isinstance(module, u.ParticleModuleColorOverLife):
                color, alpha, _ = u.FXConverterUtilitiesLibrary.get_particle_module_color_over_life_props(module)
                detail["colors"].append({"color": str(color.get_editor_property("constant_curve"))[:650] if color else None,
                                         "alpha_class": alpha.get_class().get_name() if alpha else None})
        R["particle"]["emitter_details"].append(detail)
    R["status"] = "passed"
except Exception:
    R["status"] = "failed"
    R["errors"].append(traceback.format_exc())
    u.log_error(R["errors"][-1])
(OUT / "NativeProbe.json").write_text(json.dumps(R, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if R["status"] != "passed":
    raise RuntimeError("Grab warning native probe failed")
