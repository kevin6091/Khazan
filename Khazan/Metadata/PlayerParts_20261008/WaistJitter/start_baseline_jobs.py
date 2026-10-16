ed = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
for name in ('p.RigidBodyNode.DeferredSimulationDefault', 'p.RigidBodyNode.DeferredSimulationForceDefault'):
    value = unreal.SystemLibrary.get_console_variable_int_value(name)
    assert value == 0, (name, value)
    print('Synchronous Default timing runtime:', name, value)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
monster = unreal.load_class(None, '/Script/Khazan.KZMonster')
removed = 0
for actor in unreal.GameplayStatics.get_all_actors_of_class(ed.get_editor_world(), monster):
    actors.destroy_actor(actor)
    removed += 1
print('Removed work-only unsaved AI actors:', removed)
unreal.SystemLibrary.execute_console_command(ed.get_editor_world(), 'Automation RunTests Khazan.PlayerParts.IronAudit')
