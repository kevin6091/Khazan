from pathlib import Path
main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
report = main/'Metadata/PlayerParts_20261008/ShoulderSoftening'
prepare = main/'Metadata/PlayerParts_20261008/WaistJitter/start_baseline_jobs.py'
source = prepare.read_text(encoding='utf-8').split("unreal.SystemLibrary.execute_console_command(",1)[0]
exec(compile(source,str(prepare),'exec'))
observe = report/'stock_observer.py'
exec(compile(observe.read_text(encoding='utf-8-sig'),str(observe),'exec'), {'stock_expected_pid':os.getpid()})
