from pathlib import Path
path = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/PlayerParts_20261008/WaistJitter/start_baseline_jobs.py')
source = path.read_text(encoding='utf-8').replace('Automation RunTests Khazan.PlayerParts.IronAudit', 'Automation RunTests Khazan.PlayerParts.IronContactAuthor')
exec(compile(source, str(path), 'exec'))
