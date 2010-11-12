# -*- coding: utf-8 -*-


import os
import sys

from ctypes import windll
from ctypes import cdll
from ctypes.util import find_msvcrt


def _putenv(name, value):
    '''
    :param name: environment variable name
    :param value: environment variable value

    On Microsoft Windows, starting from Python 2.4, os.environ changes only work
    within Python and no longer apply to low level C library code within the
    same process. This function calls various Windows functions to force the
    environment variable up to the C runtime.
    '''

    # Propagate new value to Windows (so SysInternals Process Explorer sees it)
    try:
        result = windll.kernel32.SetEnvironmentVariableW(name, value)

        if result == 0:
            raise Warning

        if sys.flags.verbose:
            sys.stderr.write('* pygtk-runtime: "kernel32.SetEnvironmentVariableW" successful\n')
            sys.stderr.flush()

    except Exception as inst:
        if sys.flags.verbose:
            sys.stderr.write('* pygtk-runtime: "kernel32.SetEnvironmentVariableW" failed\n')
            sys.stderr.flush()

    # Propagate new value to msvcrt (used by gtk+ runtime)
    try:
        result = cdll.msvcrt._putenv('%s=%s' % (name, value))

        if result != 0:
            raise Warning

        if sys.flags.verbose:
            sys.stderr.write('* pygtk-runtime: "msvcrt._putenv" successful\n')
            sys.stderr.flush()           

    except Exception as inst:
        if sys.flags.verbose:
            sys.stderr.write('* pygtk-runtime: "msvcrt._putenv" failed\n')
            sys.stderr.flush()

    # Propagate new value to whatever c runtime is used by python
    try:
        msvcrt = find_msvcrt()
        msvcrtname = str(msvcrt).split('.')[0] if '.' in msvcrt else str(msvcrt)
        
        result = cdll.LoadLibrary(msvcrt)._putenv('%s=%s' % (name, value))

        if result != 0:
            raise Warning

        if sys.flags.verbose:
            sys.stderr.write('* pygtk-runtime: "%s._putenv" successful\n' % msvcrtname)
            sys.stderr.flush()           

    except Exception as inst:
        if sys.flags.verbose:
            sys.stderr.write('* pygtk-runtime: "%s._putenv" failed\n' % msvcrtname)
            sys.stderr.flush()


if sys.platform == 'win32':
    pathsep = os.pathsep
    runtime = os.path.abspath(os.path.join(os.path.dirname(__file__), 'bin'))
    PATH = os.environ['PATH'].split(pathsep)   
    ABSPATH = [os.path.abspath(x) for x in PATH]

    if os.path.abspath(runtime) not in ABSPATH:
        if sys.flags.verbose:
            sys.stderr.write('* pygtk-runtime: prepending "%s" to PATH\n' % runtime)
            sys.stderr.write('* pygtk-runtime: original PATH="%s"\n' % pathsep.join(PATH))
            sys.stderr.flush()
        
        PATH.insert(0, runtime)
        os.environ['PATH'] = pathsep.join(PATH)
        _putenv('PATH', pathsep.join(PATH))

        if sys.flags.verbose:
            sys.stderr.write('* pygtk-runtime: modified PATH="%s"\n' % pathsep.join(PATH))
    else:
        if sys.flags.verbose:
            sys.stderr.write('* pygtk-runtime: "%s" already on PATH\n' % runtime)
            sys.stderr.flush()
