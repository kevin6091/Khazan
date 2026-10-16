param([string[]]$Paths)
# Read-only Windows Restart Manager inquiry; never shutdown/restart an application.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PlayerPartsLocks {
 [StructLayout(LayoutKind.Sequential)] public struct UniqueProcess { public int Pid; public System.Runtime.InteropServices.ComTypes.FILETIME Start; }
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct Info {
  public UniqueProcess Process;
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string AppName;
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=64)] public string ServiceName;
  public int Type; public uint Status; public uint Session; [MarshalAs(UnmanagedType.Bool)] public bool Restartable;
 }
 [DllImport("rstrtmgr.dll", CharSet=CharSet.Unicode)] public static extern int RmStartSession(out uint session, uint flags, string key);
 [DllImport("rstrtmgr.dll", CharSet=CharSet.Unicode)] public static extern int RmRegisterResources(uint session, uint count, string[] files, uint applications, IntPtr apps, uint services, IntPtr names);
 [DllImport("rstrtmgr.dll")] public static extern int RmGetList(uint session, out uint needed, ref uint count, [In,Out] Info[] infos, ref uint reason);
 [DllImport("rstrtmgr.dll")] public static extern int RmEndSession(uint session);
}
'@
$lockSession=0
$result=[PlayerPartsLocks]::RmStartSession([ref]$lockSession,0,[guid]::NewGuid().ToString('N'))
if ($result -ne 0) { throw "RmStartSession failed $result" }
try {
 $resolvedFiles=@($Paths | ForEach-Object { (Resolve-Path -LiteralPath $_).Path })
 $result=[PlayerPartsLocks]::RmRegisterResources($lockSession,$resolvedFiles.Count,$resolvedFiles,0,[IntPtr]::Zero,0,[IntPtr]::Zero)
 if ($result -ne 0) { throw "RmRegisterResources failed $result" }
 $needed=0; $count=0; $reason=0
 $result=[PlayerPartsLocks]::RmGetList($lockSession,[ref]$needed,[ref]$count,$null,[ref]$reason)
 if ($result -eq 234) {
  $count=$needed; $infos=New-Object 'PlayerPartsLocks+Info[]' $count
  $result=[PlayerPartsLocks]::RmGetList($lockSession,[ref]$needed,[ref]$count,$infos,[ref]$reason)
  if ($result -ne 0) { throw "RmGetList failed $result" }
  for($index=0; $index -lt $count; $index++) {
   $info=$infos[$index]; $process=Get-CimInstance Win32_Process -Filter ("ProcessId="+$info.Process.Pid)
   [pscustomobject]@{Pid=$info.Process.Pid;Name=$info.AppName;CommandLine=$process.CommandLine}
  }
 } elseif ($result -ne 0) { throw "RmGetList failed $result" }
} finally { [PlayerPartsLocks]::RmEndSession($lockSession) | Out-Null }
