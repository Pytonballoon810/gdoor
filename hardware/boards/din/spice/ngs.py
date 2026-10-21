"""Minimal driver for KiCad's shared ngspice.dll."""
import ctypes, os
from ctypes import c_char_p, c_int, c_void_p, c_bool, c_double, CFUNCTYPE, POINTER, Structure

KICAD_BIN = r"C:\Program Files\KiCad\10.0\bin"
os.add_dll_directory(KICAD_BIN)
dll = ctypes.CDLL(os.path.join(KICAD_BIN, "ngspice.dll"))

LOG = []
SendChar = CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
SendStat = CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
Exit = CFUNCTYPE(c_int, c_int, c_bool, c_bool, c_int, c_void_p)
BGRun = CFUNCTYPE(c_int, c_bool, c_int, c_void_p)

@SendChar
def _char(s, i, p):
    LOG.append(s.decode(errors="replace")); return 0
@SendStat
def _stat(s, i, p): return 0
@Exit
def _exit(a, b, c, d, p): return 0
@BGRun
def _bg(a, b, p): return 0

dll.ngSpice_Init(_char, _stat, _exit, None, None, _bg, None)

class VecInfo(Structure):
    _fields_ = [("name", c_char_p), ("type", c_int), ("flags", ctypes.c_short),
                ("realdata", POINTER(c_double)), ("compdata", c_void_p), ("length", c_int)]
dll.ngGet_Vec_Info.restype = POINTER(VecInfo)
dll.ngSpice_Command.argtypes = [c_char_p]

def cmd(c):
    dll.ngSpice_Command(c.encode())

def run(netlist):
    """Load a netlist (string; analysis cards inside), run it, return log tail."""
    LOG.clear()
    cmd("destroy all"); cmd("remcirc")
    lines = [l for l in netlist.strip().splitlines()]
    arr = (c_char_p * (len(lines) + 1))(*[l.encode() for l in lines], None)
    dll.ngSpice_Circ(arr)
    cmd("run")
    errs = [l for l in LOG if "rror" in l or "warning" in l.lower()]
    return errs

class CVec(Structure):
    _fields_ = [("re", c_double), ("im", c_double)]

def vec(name):
    p = dll.ngGet_Vec_Info(name.encode())
    if not p: raise KeyError(name)
    v = p.contents
    if v.realdata:
        return [v.realdata[i] for i in range(v.length)]
    cd = ctypes.cast(v.compdata, POINTER(CVec))
    return [complex(cd[i].re, cd[i].im) for i in range(v.length)]
