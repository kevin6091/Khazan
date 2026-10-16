"""Create diagnostic contact sheets from task-owned game captures."""
from pathlib import Path
import json
import sys
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[2]
out = root/'Metadata/PlayerSlashOuter_20261014'/sys.argv[1]
inventory = json.loads((root/'Metadata/PlayerSlashOuter_20261014/Audit01/Inventory.json').read_text(encoding='utf-8'))
analysis = json.loads((out/'PairAnalysis.json').read_text(encoding='utf-8'))
by_id = {r['id']:r for r in analysis}
groups = {}
for row in inventory['rows']:
    group = Path(row['asset']).parent.name
    for item in row['addons']:
        if item['bEndEvent']:
            continue
        groups.setdefault(group, []).append(item['EventId'])

font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
for group, ids in groups.items():
    width, height = 440, 280
    columns = 3 if len(ids) > 3 else 2
    rows = (len(ids)+columns-1)//columns
    canvas = Image.new('RGB',(width*columns,height*rows),(24,24,24))
    draw = ImageDraw.Draw(canvas)
    for i, effect_id in enumerate(ids):
        image = out/f'Pair_{effect_id}_F06_View1.png'
        if not image.exists():
            continue
        with Image.open(image) as original:
            # The same crop for every attack; no retouching of source screenshots.
            game = original.convert('RGB').crop((30,35,855,480))
            game.thumbnail((width-8,height-36))
            x = (i%columns)*width
            y = (i//columns)*height
            canvas.paste(game,(x+4,y+32))
        metric=by_id.get(effect_id,{})
        label=f"{metric.get('node','?')} {effect_id[-8:]} {','.join(metric.get('observed_sides',[]))}"
        draw.text((x+6,y+5),label,font=font,fill='white')
    dest=out/f'PairSheet_{group}.jpg'
    canvas.save(dest,quality=92)
    print(dest)
