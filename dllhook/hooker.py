from __future__ import unicode_literals

import ctypes
import ctypes.wintypes
import functools
import inspect
import re
import struct
import time
import types
from typing import Union

import capstone
import cffi
import six

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32
NULL = 0
invoker_count = 0
fetchable_general_registers = {'eax', 'ebx', 'ecx', 'edx', 'esi', 'edi'}
fetchable_registers = {'eax', 'esp', 'ebp'} | fetchable_general_registers
callbackers = []  # to prevent garbage collection


def error_string(errno):
    buffer_pointer = ctypes.c_wchar_p()
    kernel32.FormatMessageW(
        0x1300,  # FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS
        NULL,
        errno,
        0x0C00,  # MAKELANG(LANG_USER_DEFAULT | SUBLANG_DEFAULT)
        ctypes.byref(buffer_pointer),
        0,
        NULL
    )

    if buffer_pointer.value is None:
        raise ValueError('Failed to get message for error number {}'.format(errno))
    as_string = ctypes.wstring_at(buffer_pointer)
    kernel32.LocalFree(buffer_pointer)
    return '({:#x}) {}'.format(errno, as_string)


def get_last_error_string():
    errno = kernel32.GetLastError()
    as_astring = error_string(errno)
    return as_astring


def read_memory(address, size):
    PAGE_READWRITE = 0x4
    old_protect = ctypes.c_uint32()
    tmp = ctypes.c_uint32()
    kernel32.VirtualProtect(address, size, PAGE_READWRITE, ctypes.byref(old_protect))
    result = (ctypes.c_char * size).from_address(address).raw
    kernel32.VirtualProtect(address, size, old_protect, ctypes.byref(tmp))
    return result


def write_memory(address, content):
    PAGE_READWRITE = 0x4
    old_protect = ctypes.c_uint32()
    tmp = ctypes.c_uint32()
    kernel32.VirtualProtect(address, len(content), PAGE_READWRITE, ctypes.byref(old_protect))
    ctypes.memmove(address, ctypes.create_string_buffer(content), len(content))
    kernel32.VirtualProtect(address, len(content), old_protect, ctypes.byref(tmp))


def install_jump(source, destination):
    absolute_jmp = b'\xE9' + struct.pack('<I', (destination - source - 5) & 0xffffffff)
    write_memory(source, absolute_jmp)


def message_box(message='continue?', title='debug'):
    user32.MessageBoxW(NULL, (str(message) + '\0').encode('utf16'), (str(title) + '\0').encode('utf16'), 0)


def thiscall(function_ptr, this, *args):
    caller_mem = kernel32.VirtualAlloc(0, 4096, 0x3000, 0x40)
    print(f'caller_mem: {caller_mem:#x}')
    grab_ecx_pop_ret = b"\x8b\x4c\x24\x08\x8f\x44\x24\x04\xc3"
    ctypes.memmove(caller_mem, grab_ecx_pop_ret, len(grab_ecx_pop_ret))

    caller_type = ctypes.WINFUNCTYPE(function_ptr.restype, ctypes.c_void_p,
                                     ctypes.c_void_p, *(ctypes.c_long for _ in args))
    caller = caller_type(caller_mem)
    result = caller(function_ptr, this, *args)
    kernel32.VirtualFree(caller_mem, 0, 0x00008000)  # MEM_RELEASE
    print('freed')
    return result


def hook_dll(module_name, target_export_name_or_offset, timeout_seconds=5):
    def decorator(callback):
        if not isinstance(callback, types.FunctionType):
            raise TypeError("'callback' has to be a non-class and non-builtin function or lambda")
        start_time = time.time()
        while True:
            module_handle = kernel32.GetModuleHandleA((module_name + '\0').encode('ascii'))
            if module_handle == 0:
                errno = kernel32.GetLastError()
                if errno == 0x7e:  # ERROR_MOD_NOT_FOUND
                    if time.time() - start_time < timeout_seconds:
                        time.sleep(0.1)
                        continue
                    else:
                        raise ValueError('Unable to find module: {!r}: {}'.format(module_name, error_string(errno)))
                else:
                    raise ValueError('Unable to find module: {!r}: {}'.format(module_name, error_string(errno)))
            else:
                break

        if isinstance(target_export_name_or_offset, six.binary_type):
            target_address = kernel32.GetProcAddress(module_handle, target_export_name_or_offset)
            if target_address == NULL:
                raise ValueError('Unable to find procedure: {!r}: {}'.format(target_export_name_or_offset,
                                                                             get_last_error_string()))
        elif isinstance(target_export_name_or_offset, six.integer_types):
            # module_handle equals to base address
            target_address = module_handle + target_export_name_or_offset
        else:
            raise TypeError("'target_export_name_or_offset' has to be either offset in int or name in bytes")

        decorator_scope_vars = {'target_address': target_address}

        @functools.wraps(callback)
        def callbacker(*args, **kwargs):
            # got call from hook!
            # restore target head
            write_memory(decorator_scope_vars['target_address'], decorator_scope_vars['target_head'])
            callback(*args, **kwargs)

            # reinstall jumper
            install_jump(decorator_scope_vars['target_address'], decorator_scope_vars['invoker_address'])

        # make c wrapper for callbacker
        argspec = inspect.getargspec(callback)
        if argspec.varargs is not None or argspec.keywords is not None:
            raise ValueError("Varargs are not allowed in 'callback'")

        callbacker_c_wrapper = ctypes.CFUNCTYPE(None, *[ctypes.c_uint32] * len(argspec.args))
        callbacker_c = callbacker_c_wrapper(callbacker)
        global callbackers
        callbackers.append(callbacker_c)
        callbacker_c_address = int(ctypes.cast(callbacker_c, ctypes.c_void_p).value)

        # format code of callbacker_invoker_native in c, based on arguments of callback
        global invoker_count, fetchable_registers, fetchable_general_registers

        arg_order = 0
        for arg_name in argspec.args:
            if arg_name not in fetchable_registers:
                arg_order += 1

        invoker_c_asm = []
        for arg_name in reversed(argspec.args):
            # add asm code fetching arg_name
            if arg_name == 'esp':
                invoker_c_asm.append('push ebp')
            elif arg_name == 'ebp':
                invoker_c_asm.append('push [ebp]')
            elif arg_name in fetchable_general_registers:
                # arg is another register!
                invoker_c_asm.append('push {}'.format(arg_name))
            else:
                # arg is a standard argument!
                arg_order -= 1
                invoker_c_asm.append('push [ebp+{}]'.format(4 * arg_order + 8))

        target_head_long = read_memory(target_address, 19)
        cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        original_asm = []
        total_length = 0
        for address, size, mnemonic, op_str in cs.disasm_lite(target_head_long, target_address):
            disasm = '{} {}'.format(mnemonic, op_str)
            disasm = re.sub(r'([^:])(\[0x[0-9a-fA-F]+\])', r'\1 ds:\2', disasm)
            original_asm.append(disasm)
            total_length = address + size - target_address
            if total_length >= 5:
                break

        target_head = target_head_long[:5]
        decorator_scope_vars['target_head'] = target_head

        invoker_c_code = '''
__declspec(naked) void invoker_{count}()
{{
    __asm
    {{
        push ebp
        mov ebp, esp
        pushad
        {before_call}
        mov eax, {callbacker:#x}
        call eax
        add esp, {arg_depth:#x}
        popad
        pop ebp
        {original_asm}
        push {target_resume:#x}
        ret
    }}
}}
int invoker_{count}_addr()
{{
    return (int)invoker_{count};
}}
'''.format(count=invoker_count, before_call='\n'.join(invoker_c_asm), callbacker=callbacker_c_address,
           arg_depth=4 * len(argspec.args), original_asm='\n'.join(original_asm),
           target_resume=target_address + total_length)

        # allocate callbacker_invoker_native using cffi
        ffi = cffi.FFI()
        ffi.cdef('void invoker_{count}();int invoker_{count}_addr();'.format(count=invoker_count))
        invoker_lib = ffi.verify(invoker_c_code)
        invoker_address = getattr(invoker_lib, 'invoker_{count}_addr'.format(count=invoker_count))()
        decorator_scope_vars['invoker_address'] = invoker_address

        # install jumper to callbacker_invoker_native on target
        install_jump(target_address, invoker_address)
        invoker_count += 1
        print('target: {:#x}'.format(target_address))
        print('invoke: {:#x}'.format(invoker_address))
        print('callbacker: {:#x}'.format(callbacker_c_address))
        return callback  # return original function, not wrapped

    return decorator
