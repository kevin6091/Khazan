import pathlib,shutil,json
main=pathlib.Path(__file__).resolve().parents[2]
work=main.parent.parent/'Khazan_MonsterWork_20261006/Khazan'
for name in ['ReactionAuthoringPlan.json','MonsterAttackCollisionPlan.json']:
 source=main/'Metadata/CombatReaction_20261008'/name
 if source.is_file():
  target=work/'Metadata/CombatReaction_20261008'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
build=work/'Source/Khazan/Khazan.Build.cs'
original=(main/'Source/Khazan/Khazan.Build.cs').read_text(encoding='utf8')
marker='\n\t\t// Uncomment if you are using Slate UI'
assert marker in original
build.write_text(original.replace(marker,'\n\t\tif (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new string[] { "UnrealEd", "Json", "JsonUtilities", "AssetRegistry" });\n'+marker),encoding='utf8')
# Task-owned mailbox script; it does not inject player input. Native fixture begins PIE itself via request.
source=(main/'Scripts/Engineering/monster_isolated_editor.py').read_text(encoding='utf8')
source=source.replace('Saved/Logs/MonsterWorkEditor.log','Saved/Logs/CombatReactionEditor.log')
source=source.replace("'Path={Khazan.Heal.PIE}' in line", "'Path={Khazan.Combat.ReactionPIE}' in line or 'Path={Khazan.Heal.PIE}' in line")
target=work/'Saved/CombatReaction/isolated_mailbox.py';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source,encoding='utf8')
print('Prepared scoped author build/mailbox')
