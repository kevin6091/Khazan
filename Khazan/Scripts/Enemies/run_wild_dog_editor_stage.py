"""Run a WildDog art phase with process exit validation and isolated plugin flags."""
from __future__ import annotations
import json
import pathlib
import subprocess
import sys

PROJECT = pathlib.Path(__file__).resolve().parents[2]
ENGINE = pathlib.Path("C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64")
SCRIPTS = {"library": "import_wild_dog_library.py", "assemblies": "build_wild_dog_assemblies.py",
           "audit": "audit_wild_dog_library.py", "render": "capture_wild_dog_editor_preview.py"}


def main():
    stage = sys.argv[1]
    script = PROJECT / "Scripts/Enemies" / SCRIPTS[stage]
    log = PROJECT / "Saved/Logs" / f"WildDog_{stage}_20260915.log"
    report = PROJECT / "Saved/ImportReports" / f"WildDog_Process_{stage}_20260915.json"
    common = [str(PROJECT / "Khazan.uproject"), "-unattended", "-nosound", "-nosplash", "-NoSourceControl",
              "-DisablePlugins=ModelContextProtocol", "-EnablePlugins=GameFeatures", "-abslog=" + str(log)]
    if stage == "render":
        args = [str(ENGINE / "UnrealEditor.exe"), *common,
                "/Game/_Art/Enemies/Shared/Beasts/WildDog/Preview/L_EN_WildDog_Catalogue",
                "-RenderOffscreen", "-NoTextureStreaming", "-AllowCommandletRendering", "-ExecCmds=py " + str(script)]
    else:
        args = [str(ENGINE / "UnrealEditor-Cmd.exe"), *common, "-nullrhi", "-run=pythonscript", "-script=" + str(script)]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    with log.with_suffix(".stdout.txt").open("w", encoding="utf-8") as output:
        result = subprocess.run(args, stdout=output, stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startup)
    data = {"stage": stage, "process_exit_code": result.returncode, "log": str(log),
            "plugin_flags": ["-DisablePlugins=ModelContextProtocol", "-EnablePlugins=GameFeatures"],
            "project_config_modified": False}
    report.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps(data), flush=True)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
