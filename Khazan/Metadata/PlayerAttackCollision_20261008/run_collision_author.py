from pathlib import Path
scope={'expected_editor_pid':2252,'__name__':'attack_author'}
exec(compile(Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Scripts/Engineering/player_attack_collision_author_20261008.py').read_text(encoding='utf-8'),'player_attack_collision_author_20261008.py','exec'),scope)
r=scope['AUTHOR_RESULT']
print({k:r.get(k) for k in ('success','before_sha256','after_sha256','limitations','mutations')})
print([(n['node_id'],n['window_count'],sum(w['key_count'] for w in n['windows'])) for n in r['nodes']])
