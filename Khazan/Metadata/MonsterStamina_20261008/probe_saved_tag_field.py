import unreal
effect = unreal.get_default_object(unreal.load_class(None, '/Game/Monsters/Effects/GE_DeadState.GE_DeadState_C'))
for component in effect.get_editor_property('ge_components'):
    print(component.get_class().get_name())
    for field in ['InheritableGrantedTagsContainer', 'inheritable_granted_tags_container', 'add_tags', 'AddTags']:
        try:
            print(field, component.get_editor_property(field).export_text())
        except Exception as error:
            print(field, 'unexposed', str(error))
