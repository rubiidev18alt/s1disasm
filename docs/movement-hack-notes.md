# Movement hack notes

This branch adds a source-only movement patcher and a GitHub Actions build workflow.

## Added behavior

- Raises Sonic's normal speed variable to `$3FFF`, which effectively removes the normal ground and air speed cap while avoiding common 16-bit overflow traps.
- Raises the direct rolling speed clamps in `Sonic_AngledRollSpeed` to `$3FFF` / `-$3FFF`.
- Adds a Sonic CD-style spin dash using existing Sonic 1 rolling sprites and the existing roll sound.
  - Hold Down, press A/B/C to charge, release Down to launch.
- Adds a peelout using existing run sprites and in-game sound IDs.
  - Hold Up and A/B/C from standstill, then release Up or the button to launch.
- Adds an extended camera lead.
  - At high horizontal speed, the foreground camera is nudged in Sonic's travel direction while respecting level boundaries and boss locks.
- Adds a homing attack / air dash.
  - Press A/B/C in the air.
  - If a nearby monitor or known badnik is found, Sonic homes toward it in ball state so existing collision logic destroys the target.
  - If no target is nearby, Sonic performs a fast air dash in his facing direction.

## Build workflow

`.github/workflows/build-rom.yml` installs Lua, applies `tools/apply_movement_mods.py`, runs the existing `build.lua`, verifies `s1built.bin`, and uploads the produced Genesis ROM as a workflow artifact.

The workflow does not download commercial ROMs or external copyrighted assets. It only builds from the repository contents.

## Notes

The patcher is idempotent. Running it more than once should not duplicate the new routines.

Because this is a large movement patch inserted into an old 68k engine, the first real test should be GHZ1 with monitors, badniks, slopes, water transitions, and debug mode disabled. Watch for camera boundary weirdness and target priority issues.
