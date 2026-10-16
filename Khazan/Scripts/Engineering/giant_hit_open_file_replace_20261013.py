from pathlib import Path
import ctypes,ctypes.wintypes as wt,os,json
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.CreateFileW.argtypes=[wt.LPCWSTR,wt.DWORD,wt.DWORD,ctypes.c_void_p,wt.DWORD,wt.DWORD,ctypes.c_void_p];k.CreateFileW.restype=wt.HANDLE
k.SetFileInformationByHandle.argtypes=[wt.HANDLE,ctypes.c_int,ctypes.c_void_p,wt.DWORD];k.SetFileInformationByHandle.restype=wt.BOOL
k.CloseHandle.argtypes=[wt.HANDLE];k.CloseHandle.restype=wt.BOOL

def replace_open_file(source,destination):
 source=source.resolve();destination=destination.resolve();assert source.parent==destination.parent
 name=str(destination)
 class Info(ctypes.Structure):_fields_=[('Flags',wt.DWORD),('RootDirectory',wt.HANDLE),('FileNameLength',wt.DWORD),('FileName',wt.WCHAR*(len(name)+1))]
 info=Info();info.Flags=3;info.RootDirectory=None;info.FileNameLength=len(name.encode('utf-16-le'));info.FileName=name
 handle=k.CreateFileW(str(source),0x10000,7,None,3,0,None)
 if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
 try:
  if not k.SetFileInformationByHandle(handle,22,ctypes.byref(info),ctypes.sizeof(info)):raise ctypes.WinError(ctypes.get_last_error())
 finally:k.CloseHandle(handle)

if __name__=='__main__':
 p=Path(__file__).resolve().parents[2]/'Metadata/GiantHitOverlay_20261013/PosixReplaceProof';assert not p.exists();p.mkdir()
 old=p/'target.bin';new=p/'replacement.bin';alias=p/'old_hardlink.bin';old.write_bytes(b'old-generation');new.write_bytes(b'new-generation');os.link(old,alias)
 handle=k.CreateFileW(str(old),0x80000000,3,None,3,0,None);assert handle!=ctypes.c_void_p(-1).value
 try:replace_open_file(new,old)
 finally:k.CloseHandle(handle)
 assert old.read_bytes()==b'new-generation' and alias.read_bytes()==b'old-generation';print('Open target replacement and old hardlink preservation verified')