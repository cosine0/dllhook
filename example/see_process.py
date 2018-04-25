import ctypes
import dllhook


@dllhook.hook_dll('Kernel32.dll', b'CreateProcessW')
def see_process(arg1):
    if arg1 != 0:
        print(ctypes.wstring_at(arg1))
