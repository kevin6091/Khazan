"""Register the project's visual combat VFX editor commands."""
import unreal

try:
    import kz_combat_vfx_sequencer
    kz_combat_vfx_sequencer.register_menus()
except Exception as error:
    unreal.log_warning('Khazan VFX menu could not be registered: ' + str(error))
