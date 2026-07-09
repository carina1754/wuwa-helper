"""WuWa damage/DPS engine (backend-canonical).

A faithful Python port of the proven client oracle ``frontend/src/lib/build.ts``
(the phro.love-style 8-term damage formula). ``formula.py`` holds the pure math;
``stats.py`` assembles a build into final stats; the loader/engine wire it to the
DB. Parity with build.ts is asserted by fixed-vector tests.
"""
