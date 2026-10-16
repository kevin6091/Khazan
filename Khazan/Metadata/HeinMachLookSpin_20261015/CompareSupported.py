"""Colour evidence excludes empty background; retain old full-ROI diagnostics."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parent
main=root.parents[1]
source=(main/'Scripts/Art/compare_heinmach_vfx_colours_20261015.py').read_text(encoding='utf-8')
source=source.replace("energy=ImageStat.Stat(absolute).sum\n    emission=ImageStat.Stat(foreground).sum", "support_mask=absolute.convert('L').point(lambda x:255 if x>12 else 0)\n    energy=ImageStat.Stat(absolute,support_mask).sum\n    emission=ImageStat.Stat(foreground,support_mask).sum",1)
source=source.replace("method':'background-subtracted colour/energy signatures; native random particle shapes vary", "method':'background-subtracted colour/energy only over visible support >12; exclude empty-panel drift; native random shapes vary",1)
sys.argv=[sys.argv[0]]+[str((root/arg).resolve()) for arg in sys.argv[1:4]]
exec(compile(source,__file__,'exec'),globals())
