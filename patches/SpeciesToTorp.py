# SpeciesToTorp.py - Torpedo type constants for multiplayer network sync
# Rebuilt from .py script scanning + known BC/KM constants from .pyc files
# Uses sys.modules replacement so unknown constants auto-assign unique IDs

import sys

class _SpeciesToTorp:
    PHOTON       = 0
    PHOTON1      = 1
    PHOTON2      = 2
    PHOTON3      = 3
    PHOTON4      = 4
    PHOTON4A     = 5
    PHOTON5      = 6
    PHOTON6      = 7
    PHOTON7      = 8
    PHOTON8      = 9
    PLASMA       = 10
    PLASMA2      = 11
    PLASMA3      = 12
    PLASMA4      = 13
    QUANTUM      = 14
    QUANTUM2     = 15
    QUANTUM3     = 16
    QUANTUM4     = 17
    DISRUPTOR    = 18
    DISRUPTOR1   = 19
    DISRUPTOR2   = 20
    DISRUPTOR3   = 21
    DISRUPTOR4   = 22
    FUSIONBOLT   = 23
    FUSIONBOLT2  = 24
    PULSEPHASER  = 25
    MISSILE      = 26
    MISSILE1P    = 27
    MISSILE2     = 28
    CHRONITON    = 29
    TRANSPHASIC  = 30
    TRICOBALT    = 31
    GRAVIMETRIC  = 32
    NEUTRONIC    = 33
    BIOMOLECULAR = 34
    KRENIMPULSE  = 35
    REDIRECT     = 36
    PHASEDPLASMA = 37
    _next        = 38

    def __getattr__(self, name):
        val = self._next
        self._next = self._next + 1
        setattr(self, name, val)
        return val

sys.modules[__name__] = _SpeciesToTorp()
