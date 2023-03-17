dllhook
===
[![PyPI version](https://badge.fury.io/py/dllhook.svg)](https://badge.fury.io/py/dllhook)  
dllhook is a tool for hooking Windows x86 applications. This tools injects embedded Python interpreter (Python DLL)
to the application and executes your script. And also this provides a convenient hooking library to use in your script.  
This tool uses `mayhem python_injector` as injector.  
See https://github.com/zeroSteiner/mayhem/blob/master/tools/python_injector.py  
When you clone this repository, you must also clone submodule `mayhem`.  
This tool is tested on Python 3.6-3.11.

Installation
===
Make sure you use 32-bit version of Python.  

To install dllhook:
```shell
pip install dllhook
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
        print("<hooked> ", ctypes.wstring_at(arg1))
```
* Save it as a file. (e.g. `C:\Users\example\Desktop\see_process.py`)

* Execute the module `dllhook` with the target program and your script as the arguments.
```shell
python -mdllhook "C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe" C:\Users\example\Desktop\see_process.py
```
Console output:
```text
[+] Opened a handle to pid: 24308
[*] Found Python library at: C:\Users\example\AppData\Local\Programs\Python\Python36-32\python36.dll
[*] Injecting Python into the process...
[+] Loaded C:\Users\example\AppData\Local\Programs\Python\Python36-32\python36.dll with handle 0x69ee0000
[*] Resolved addresses:
  - Py_InitializeEx:    0x6a061cc0
  - PyRun_SimpleString: 0x6a07b1c0
[*] Initialized Python in the host process
[*] Waiting for client to connect on \\.\pipe\mayhem
[*] Client connected on named pipe
target: 0x75ae4510
invoke: 0x6c401df0
callbacker: 0x6620fdc
<hooked> C:/Program Files (x86)/Adobe/Acrobat Reader DC/Reader/ARH.exe
<hooked> C:\Program Files (x86)\Common Files\Adobe\ARM\1.0\AdobeARM.exe
```
Author
===
[cosine0](https://github.com/cosine0) @github
