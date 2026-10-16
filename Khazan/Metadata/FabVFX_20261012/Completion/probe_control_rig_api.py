import unreal,json
print(json.dumps({'rig_api':[n for n in dir(unreal.ControlRigBlueprint) if any(s in n.lower() for s in ('compile','vm','model'))], 'blueprint_api':[n for n in dir(unreal.BlueprintEditorLibrary) if 'compile' in n.lower()]}))
