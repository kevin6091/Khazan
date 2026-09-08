"""Run once via UnrealEditor-Cmd -run=pythonscript, with the GUI closed.

Texture decoding/import is kept out of the live Rider task-graph callback.
The underlying importer explicitly uses legacy TextureFactory, not Interchange.
"""
import os
import runpy

root = os.path.normpath(os.path.join(os.path.dirname(__file__), '../..'))
module = runpy.run_path(os.path.join(root, 'Scripts/StormPass/restore_stormpass_subsurface_inputs.py'))
textures = module['import_textures']()
print('STORMPASS_TEXTURE_IMPORT_COMPLETE count=%d' % len(textures))
