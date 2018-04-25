import argparse
import inspect
import os
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename))
INTERPRETER_DIR = os.path.dirname(os.path.abspath(sys.executable))

injected_script = '''
import imp
import time
import os
imp.load_source('injected', {import_path!r})

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
    script_path = args.python_script
    pid = subprocess.Popen(exe_path).pid

    injector_path = os.path.join(SCRIPT_DIR, 'mayhem', 'tools', 'python_injector.py')
    envs = os.environ.copy()

    if 'PATH' in os.environ:
        envs['PATH'] = os.path.pathsep.join([r'C:\windows\syswow64', INTERPRETER_DIR, os.environ['PATH']])
    else:
        envs['PATH'] = INTERPRETER_DIR

    f = tempfile.NamedTemporaryFile(suffix='.py', delete=False)
    formatted_script = injected_script.format(working_dir=os.path.abspath(os.curdir),
                                              import_path=script_path).encode('utf8')

    f.write(formatted_script)
    f.close()

    subprocess.Popen([sys.executable, injector_path, f.name, str(pid)],
                     env=envs).wait()

    os.unlink(f.name)
