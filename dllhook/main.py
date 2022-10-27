import argparse
import inspect
import os
import subprocess
import sys
import tempfile
from pathlib import Path

MAIN_DIR = os.path.dirname(os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename))
INTERPRETER_DIR = os.path.dirname(os.path.abspath(sys.executable))

injected_script = '''
import time
{venv_setup}
with open({script_path!r}) as f:
    exec(f.read())

while True:
    time.sleep(1)
'''


def main():
    parser = argparse.ArgumentParser(
        description='Execute target exe file and inject python script to it using dll injection.')
    parser.add_argument('exe', help='target exe file')
    parser.add_argument('python_script', help='python script file to inject')
    args = parser.parse_args()

    exe_path = args.exe
    script_path = os.path.abspath(args.python_script)
    pid = subprocess.Popen(exe_path).pid

    envs = os.environ.copy()

    if 'PATH' in os.environ:
        envs['PATH'] = os.path.pathsep.join([r'C:\windows\syswow64', INTERPRETER_DIR, os.environ['PATH']])
    else:
        envs['PATH'] = INTERPRETER_DIR

    if os.path.basename(INTERPRETER_DIR).lower() == 'scripts':
        # in venv
        library_path = Path(INTERPRETER_DIR) / 'lib' / 'site-packages'
        venv_setup = f'import sys\nsys.path.append(' \
                     f'{library_path.absolute().as_posix()!r})'
    else:
        venv_setup = ''

    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
        formatted_script = injected_script.format(working_dir=os.path.abspath(os.curdir),
                                                  script_path=script_path,
                                                  venv_setup=venv_setup).encode('utf_8')
        f.write(formatted_script)

    injector_path = Path(MAIN_DIR) / 'mayhem' / 'tools' / 'python_injector.py'
    subprocess.Popen([sys.executable, injector_path, f.name, str(pid)],
                     env=envs).wait()
    os.unlink(f.name)
