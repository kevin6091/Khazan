"""Reuse the existing accepted-hit/attack PIE suites in a task-owned editor."""
from pathlib import Path
import os
import unreal as u
main=Path(os.environ['KZ_HM_COLOUR_MAIN']);project=Path(u.Paths.project_dir()).resolve()
work=main.parent.parent/'Khazan_HeinColourVFXWork_20261015'/'Khazan'
assert project in (main,work)
level='/Game/Maps/L_HeinMach_Environment' if os.environ.get('KZ_HM_COLOUR_LEVEL')=='HeinMach' else '/Game/Maps/DevMap'
if 'Khazan.CombatEffect.PIE' in os.environ.get('KZ_HM_COLOUR_TEST',''):
    import shutil
    rel='Metadata/CombatImpactUpgrade_20261012/WeaponSlashProbe04/WeaponProbe.json'
    if project!=main:
        (project/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(main/rel,project/rel)

def seed_fixture_families():
    # QA only: HeinMach has a selected gameplay family, while the existing
    # integration suites require four/six initialized families. Save nothing.
    if not level.endswith('L_HeinMach_Environment'):return
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    start=next(actor for actor in actors.get_all_level_actors() if isinstance(actor,u.PlayerStart)).get_actor_location()
    # Existing placed/seeded AI must not attack the subject during the isolated
    # montage review. New test-owned victims retain their actual class defaults.
    for actor in actors.get_all_level_actors():
        if isinstance(actor,u.KZMonster):
            actor.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
            actor.set_editor_property('ai_controller_class',None)
    for index,name in enumerate(('Swordsman','SwordShield','HeavySwordsman','HalberdElite')):
        cls=u.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_'+name+'.BP_Monster_'+name+'_C');assert cls,name
        actor=actors.spawn_actor_from_class(cls,start+u.Vector(20000+300*(index+1),0,300))
        actor.set_actor_label('QA_ColourHit_'+name)
        actor.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
        actor.set_editor_property('ai_controller_class',None)
        actor.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_NONE)
test=os.environ.get('KZ_HM_COLOUR_TEST','Khazan.Parry.PIE')
os.environ.update(KZ_MONSTER_REPAIR_OUT=os.environ['KZ_HM_COLOUR_OUT'],KZ_MONSTER_REPAIR_MODE='rhi',
                  KZ_MONSTER_REPAIR_TEST=test,KZ_COMBAT_UI_OUTPUT=os.environ['KZ_HM_COLOUR_OUT'],
                  KZ_PARRY_OUT=os.environ['KZ_HM_COLOUR_OUT'])
if 'Khazan.MonsterRepair.PIE' in test:
    import shutil
    shutil.copy2(main/'Metadata/MonsterRootCollisionRepair_20261012/AttackCases.tsv',
                 Path(os.environ['KZ_HM_COLOUR_OUT'])/'AttackCases.tsv')
if ',' in test:
    os.environ.update(KZ_MONSTER_PHYSICS_OUT=os.environ['KZ_HM_COLOUR_OUT'],KZ_MONSTER_PHYSICS_TESTS=test)
    source=(main/'Scripts/Engineering/monster_physics_validation_driver_20261013.py').read_text(encoding='utf-8')
    old="assert PROJECT in (MAIN,MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan')"
    assert source.count(old)==1
    source=source.replace(old,'assert PROJECT == Path('+repr(str(project))+')',1)
    source=source.replace("load_level('/Game/Maps/DevMap')","load_level("+repr(level)+")",1)
    source=source.replace("START=LAST=time.monotonic()","seed_fixture_families()\nSTART=LAST=time.monotonic()",1)
    old="if test.endswith('.PIE') or test.endswith('KnockbackPIE'):"
    assert source.count(old)==1
    source=source.replace(old,"if (test.endswith('.PIE') or test.endswith('KnockbackPIE')) and test not in ('Khazan.MonsterRepair.PIE','Khazan.CombatEffect.PIE'):",1)
    # Report native material failures alongside gameplay completion.
    source=source.replace("(OUT/'Driver.json').write_text", "report['material_compile_failures']=[line for line in (OUT/'Editor.log').read_text(encoding='utf-8',errors='replace').splitlines() if 'Failed to compile Material' in line or 'Default Material will be used' in line]\n    if report['material_compile_failures']:report['status']='failed'\n    (OUT/'Driver.json').write_text",1)
    exec(compile(source,__file__,'exec'),globals())
else:
    source=(main/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
    old="assert ROOT in [Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan'),Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')]"
    assert source.count(old)==1
    source=source.replace(old,'assert ROOT == Path('+repr(str(project))+')',1)
    source=source.replace("load_level('/Game/Maps/DevMap')","load_level("+repr(level)+")",1)
    source=source.replace("START=time.monotonic()","seed_fixture_families()\nSTART=time.monotonic()",1)
    exec(compile(source,__file__,'exec'),globals())
