"""Export only the two source-linked flare textures for mask inspection."""
from pathlib import Path
import os
import unreal as u

OUT = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
for name, path in [
    ('Tex_Emi', '/Game/_Art/Effects/Shared/Textures/BBQ_Texture/Flare/FT_Flare_004_LSY'),
    ('Tex_OPA', '/Game/_Art/Effects/Shared/Textures/External/T_GradientGlow'),
]:
    texture = u.load_asset(path)
    assert texture
    task = u.AssetExportTask()
    task.object = texture
    task.filename = str(OUT / (name + '.png'))
    task.exporter = u.TextureExporterPNG()
    task.automated = True
    task.prompt = False
    assert u.Exporter.run_asset_export_task(task), name
