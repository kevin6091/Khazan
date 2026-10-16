"""Apply only the requested Guard VFX and giant AI settings, with package backups."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ["KZ_COMBAT_FEEL_OUT"])
OUT.mkdir(parents=True, exist_ok=True)
PATHS = ["/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard"] + [
    "/Game/Bluprints/Monsters/BP_Monster_" + family for family in ("ApesStoneHandElite", "Yetuga")]
report = {"status": "running", "project": str(ROOT), "backups": [], "saved": [], "brutal_particles": []}

def ref(obj):
    return obj.get_path_name() if obj else None

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def defaults(bp):
    return unreal.get_default_object(unreal.load_class(None, bp.get_path_name() + "_C"))

try:
    assert ROOT == Path(__file__).resolve().parents[2], "Only the main project is authorized here"
    packages = {path: unreal.load_asset(path) for path in PATHS}
    assert all(packages.values())
    dirty = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    assert not dirty.intersection(PATHS), "Target has unsaved changes"
    guard = defaults(packages[PATHS[0]])
    guard.get_editor_property("ParryBrutalEffects")  # New standard module, not an older loaded DLL.
    distortion = unreal.load_asset("/Game/VFX/03_SlashHit/KZ_Parring_Distort")
    assert distortion
    montage = unreal.load_asset("/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/AM_DAS_BrutalFront")
    assert montage
    # Reuse the current saved Brutal effects, including unit-fixed materials and
    # per-instance parameters. Ground dust/decal/trail geometry is not a parry contact.
    source_effects = {}
    for event in unreal.AnimationLibrary.get_animation_notify_events(montage):
        parent = event.get_editor_property("notify")
        if not isinstance(parent, unreal.KZAnimNotify_CombatEffect):
            continue
        for effect in [parent] + list(parent.get_editor_property("BatchedEffects")):
            particle = effect.get_editor_property("ParticleTemplate")
            if not particle or effect.get_editor_property("bEndEvent") or effect.get_editor_property("bSpawnOnFloor"):
                continue
            # Reuse the Brutal hit's actual contact particles. Its actor/weapon
            # animation trails are not contact bursts and produce unrelated arm
            # geometry when the Guard success pose replaces the paired animation.
            if particle.get_name() not in ("PP_AtkEx_Grapple_01", "PP_AtkEx_Grapple_02", "PP_Dmg_Blood_Trail_Sub"):
                continue
            key = (ref(particle), str(effect.get_editor_property("SourceSocket")))
            source_effects.setdefault(key, effect)
    assert source_effects and any("PP_AtkEx_Grapple_02" in key[0] for key in source_effects)
    # Copy only serialized data fields declared by the existing renderer class.
    header = (ROOT / "Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.h").read_text(encoding="utf-8-sig")
    body = header.split("class KHAZAN_API UKZAnimNotify_CombatEffect", 1)[1]
    fields = re.findall(r"UPROPERTY\([^\n]*\)\s*(?://[^\n]*\n\s*)*(?:[\w:<>,*]+\s+)+(\w+)\s*(?:=|;)", body)
    assert "ParticleTemplate" in fields and "InstanceParameters" in fields and "Scale3D" in fields
    for path in PATHS:
        current = ROOT / "Content" / (path.removeprefix("/Game/") + ".uasset")
        backup = OUT / "Before" / (path.removeprefix("/Game/") + ".uasset")
        backup.parent.mkdir(parents=True, exist_ok=True)
        assert current.is_file()
        shutil.copy2(current, backup)
        assert sha(current) == sha(backup)
        report["backups"].append({"asset": path, "file": str(current), "backup": str(backup), "before_sha256": sha(current)})
    copies = []
    for index, (key, source) in enumerate(source_effects.items()):
        copy = unreal.new_object(unreal.KZAnimNotify_CombatEffect, outer=guard, name="ParryBrutal_%02d" % index)
        assert copy
        for field in fields:
            if field != "BatchedEffects":
                copy.set_editor_property(field, source.get_editor_property(field))
        copy.set_editor_property("BatchedEffects", [])
        copies.append(copy)
        report["brutal_particles"].append({"particle": key[0], "socket": key[1], "source_notify": ref(source),
                                           "source_package": source.get_editor_property("SourcePackage"),
                                           "source_field": source.get_editor_property("SourceField"),
                                           "window_start": source.get_editor_property("WindowStartTime"),
                                           "window_end": source.get_editor_property("WindowEndTime")})
    guard.set_editor_property("ParryBrutalEffects", copies)
    guard.set_editor_property("ParryBillboardDistortion", distortion)
    guard.set_editor_property("ParryBillboardDistortionScale", 1.)  # Requested asset native unit scale.
    guard.set_editor_property("ParryBillboardDistortionTailSeconds", .5)  # TEMP emission only; retain alpha drain.
    report["giant_settings"] = []
    for family, path in zip(("ApesStoneHandElite", "Yetuga"), PATHS[1:]):
        cdo = defaults(packages[path])
        settings = cdo.get_editor_property("AISettings")
        settings.set_editor_property("bDirectPursuitWhenPathFails", True)
        if family == "Yetuga":
            settings.set_editor_property("RangedPatternSkill", "Armageddon")
            # Source distance split BT058 MaxDist=800; source Armageddon BT037 Max=5000, cm.
            settings.set_editor_property("RangedPatternDistance", unreal.Vector2D(800., 5000.))
            settings.set_editor_property("RangedPatternChance", .3)  # Assistant TEMP, user permits natural values.
            settings.set_editor_property("RangedPatternCooldownSeconds", 20.)  # TEMP: readable recurrence instead of source 240s.
        cdo.set_editor_property("AISettings", settings)
        report["giant_settings"].append({"family": family, "settings": settings.export_text()})
    for path, bp in packages.items():
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        assert unreal.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False), path
        report["saved"].append(path)
    assert len(defaults(packages[PATHS[0]]).get_editor_property("ParryBrutalEffects")) == len(copies)
    for entry in report["backups"]:
        entry["after_sha256"] = sha(Path(entry["file"]))
    report["copied_effect_fields"] = fields
    report["status"] = "passed"
except Exception:
    report["status"] = "failed"
    report["error"] = traceback.format_exc()
    unreal.log_error(report["error"])
    for entry in report["backups"]:
        shutil.copy2(entry["backup"], entry["file"])
        assert sha(Path(entry["file"])) == entry["before_sha256"]
    report["rollback"] = "all backed-up package hashes restored"
finally:
    (OUT / "Author.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log("COMBAT_FEEL_AUTHOR " + report["status"])
    unreal.SystemLibrary.quit_editor()
