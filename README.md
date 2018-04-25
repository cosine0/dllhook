dllhook
===
dllhook is a tool for hooking window x86 applications. This tools injects embedded Python interpreter (Python DLL)
to the application and executes your script. And also this provides a convenient hooking library to use in your script.  
This tool uses `mayhem python_injector` as injector.  
See https://github.com/zeroSteiner/mayhem/blob/master/tools/python_injector.py  
When you clone this repository, you must also clone submodule `mayhem`.  
This tool is tested on Python 3.6.

Installation
===
Make sure you use 32-bit version of Python.  
This package requires `capstone`. To install `capstone`, in _Visual Studio Developer Command Prompt_:
```shell
python -mpip install capstone
```

To install dllhook:
```shell
python -mpip install dllhook
```

Usage
===
* Write your python script to inject.
```python
import ctypes
import dllhook

# @dllhook.hook_dll('Kernel32.dll', 0x00014510) also works
@dllhook.hook_dll('Kernel32.dll', b'CreateProcessW')
def see_process(arg1):
    if arg1 != 0:
        print(ctypes.wstring_at(arg1))
```
* Save it as a file. (e.g. `C:\Users\example\Desktop\see_process.py`)

* execute module `dllhook` with the target program and the script as the arguments and enjoy!
```shell
python -mdllhook "C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe" C:\Users\example\Desktop\see_process.py
```

Author
===
[cosine0](https://github.com/cosine0) @github