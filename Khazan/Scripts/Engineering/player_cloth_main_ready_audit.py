"""Reuse the existing read-only Original-parts audit for the cloth journal."""
from pathlib import Path
source = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Scripts/Engineering/player_hair_main_ready_audit.py')
globals().setdefault('cloth_report_directory', source.parents[2] / 'Metadata/PlayerParts_20261007/ClothRefinement')
exec(compile(source.read_text(encoding='utf-8-sig'), str(source), 'exec'))
