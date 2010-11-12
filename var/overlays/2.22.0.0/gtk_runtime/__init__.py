# -*- coding: utf-8 -*-


import os
import sys

from ctypes import windll
from ctypes import cdll
from ctypes.util import find_msvcrt


verbose = sys.flags.verbose


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
        if result == 0: raise Warning
    except Exception as inst:
        if verbose:
            sys.stderr.write('gtk+-runtime: kernel32.SetEnvironmentVariableW failed\n')
            sys.stderr.flush()

    # Propagate new value to msvcrt (used by gtk+ runtime)
    try:
        result = cdll.msvcrt._putenv('%s=%s' % (name, value))
        if result == -1: raise Warning
    except Exception as inst:
        if verbose:
            sys.stderr.write('gtk+-runtime: msvcrt._putenv failed\n')
            sys.stderr.flush()

    # Propagate new value to whatever c runtime is used by python
    try:
        result = cdll.LoadLibrary(find_msvcrt())._putenv('%s=%s' % (name, value))
        if result == -1: raise Warning
    except Exception as inst:
        if verbose:
            sys.stderr.write('gtk+-runtime: python msvcr?._putenv failed\n')
            sys.stderr.flush()


if sys.platform == 'win32':
    runtime = os.path.abspath(os.path.join(os.path.dirname(__file__), 'bin'))
    path = os.environ['PATH'].split(';')
    
    if verbose:
        sys.stderr.write('gtk+-runtime: original PATH=%s\n' % path)
        sys.stderr.flush()
    
    path.insert(1, runtime)
    
    if verbose:
        sys.stderr.write('gtk+-runtime: modified PATH=%s\n' % path)
        sys.stderr.flush()
        
    _putenv('PATH', ';'.join(path))
