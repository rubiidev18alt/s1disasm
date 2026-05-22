#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SONIC_OBJ = ROOT / "_incObj" / "01 Sonic.asm"
SONIC_MAIN = ROOT / "sonic.asm"
NO_CAP_SPEED = "$3FFF"
MARKER_OBJ = "; Rubii movement hack additions"
MARKER_MAIN = "; Rubii extended camera routine"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", newline="")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def must_replace(text: str, old: str, new: str, name: str) -> str:
    if old not in text:
        raise RuntimeError(f"Could not find patch anchor: {name}")
    return text.replace(old, new, 1)


def replace_in_block(text: str, start: str, end: str, replacements: dict[str, str]) -> str:
    start_i = text.find(start)
    if start_i == -1:
        raise RuntimeError(f"Could not find block start: {start}")
    end_i = text.find(end, start_i)
    if end_i == -1:
        raise RuntimeError(f"Could not find block end after {start}: {end}")
    block = text[start_i:end_i]
    for old, new in replacements.items():
        block = block.replace(old, new)
    return text[:start_i] + block + text[end_i:]


def remove_speed_caps(text: str) -> str:
    text = re.sub(
        r"move\.w\t#\$(?:300|600|C00),\(v_sonspeedmax\)\.w",
        f"move.w\t#{NO_CAP_SPEED},(v_sonspeedmax).w",
        text,
    )
    return replace_in_block(
        text,
        "Sonic_AngledRollSpeed:",
        "; End of function Sonic_RollSpeed",
        {
            "cmpi.w\t#$1000,d0": "cmpi.w\t#$3FFF,d0",
            "move.w\t#$1000,d0": "move.w\t#$3FFF,d0",
            "cmpi.w\t#-$1000,d0": "cmpi.w\t#-$3FFF,d0",
            "move.w\t#-$1000,d0": "move.w\t#-$3FFF,d0",
            "cmpi.w\t#$1000,d1": "cmpi.w\t#$3FFF,d1",
            "move.w\t#$1000,d1": "move.w\t#$3FFF,d1",
            "cmpi.w\t#-$1000,d1": "cmpi.w\t#-$3FFF,d1",
            "move.w\t#-$1000,d1": "move.w\t#-$3FFF,d1",
        },
    )


def patch_sonic_modes(text: str) -> str:
    if "Sonic_CDAction" in text and "Sonic_HomingAttack" in text:
        return text

    text = must_replace(text, """Sonic_MdNormal:\t; While Sonic is on the ground and not rolling
\t\tbsr.w\tSonic_Jump\t\t\t\t; check if we need to jump
\t\tbsr.w\tSonic_SlopeResistWalk\t\t\t; handle resistance from running up slopes
\t\tbsr.w\tSonic_Move\t\t\t\t; handle Sonic's left/right movement
\t\tbsr.w\tSonic_Roll\t\t\t\t; check if we need to roll
\t\tbsr.w\tSonic_LevelBound\t\t\t; make sure Sonic stays within level bounds and handle bottomless pits
\t\tjsr\t(SpeedToPos).l\t\t\t\t; update Sonic's position based on his current velocities
\t\tbsr.w\tSonic_AnglePos\t\t\t\t; update Sonic's current angle as he walks along the floor
\t\tbsr.w\tSonic_SlopeRepel\t\t\t; handle Sonic detaching from walls if not fast enough
\t\trts
""", """Sonic_MdNormal:\t; While Sonic is on the ground and not rolling
\t\tclr.b\t(v_unused3).w\t\t\t\t; reset homing attack once Sonic is grounded
\t\tbsr.w\tSonic_CDAction\t\t\t\t; handle spin dash/peelout charge and release
\t\tbcs.s\t.cdactiondone\t\t\t\t; if charging or launching, skip normal ground controls
\t\tbsr.w\tSonic_Jump\t\t\t\t; check if we need to jump
\t\tbsr.w\tSonic_SlopeResistWalk\t\t\t; handle resistance from running up slopes
\t\tbsr.w\tSonic_Move\t\t\t\t; handle Sonic's left/right movement
\t\tbsr.w\tSonic_Roll\t\t\t\t; check if we need to roll
\t\tbsr.w\tSonic_LevelBound\t\t\t; make sure Sonic stays within level bounds and handle bottomless pits
\t\tjsr\t(SpeedToPos).l\t\t\t\t; update Sonic's position based on his current velocities
\t\tbsr.w\tSonic_AnglePos\t\t\t\t; update Sonic's current angle as he walks along the floor
\t\tbsr.w\tSonic_SlopeRepel\t\t\t; handle Sonic detaching from walls if not fast enough
.cdactiondone:
\t\trts
""", "Sonic_MdNormal")

    text = must_replace(text, """Sonic_MdJump:\t; While Sonic is in the air but not rolling
\t\tbsr.w\tSonic_JumpHeight\t\t\t; handle Sonic's jump height based on whether the jump button is still held
""", """Sonic_MdJump:\t; While Sonic is in the air but not rolling
\t\tbsr.w\tSonic_HomingAttack\t\t\t; homing attack/air dash on jump button press
\t\tbsr.w\tSonic_JumpHeight\t\t\t; handle Sonic's jump height based on whether the jump button is still held
""", "Sonic_MdJump")

    text = must_replace(text, """Sonic_MdRoll:\t; While Sonic is on the ground and rolling
\t\tbsr.w\tSonic_Jump\t\t\t\t; check if we need to jump
""", """Sonic_MdRoll:\t; While Sonic is on the ground and rolling
\t\tclr.b\t(v_unused3).w\t\t\t\t; reset homing attack once Sonic is grounded
\t\tbsr.w\tSonic_Jump\t\t\t\t; check if we need to jump
""", "Sonic_MdRoll")

    return must_replace(text, """Sonic_MdJump2:\t; While Sonic is in the air and rolling (usually, but not limited to, jumping)
\t\tbsr.w\tSonic_JumpHeight\t\t\t; handle Sonic's jump height based on whether the jump button is still held
""", """Sonic_MdJump2:\t; While Sonic is in the air and rolling (usually, but not limited to, jumping)
\t\tbsr.w\tSonic_HomingAttack\t\t\t; homing attack/air dash on jump button press
\t\tbsr.w\tSonic_JumpHeight\t\t\t; handle Sonic's jump height based on whether the jump button is still held
""", "Sonic_MdJump2")


MOVEMENT_ROUTINES = r'''

; ===========================================================================
; Rubii movement hack additions
; v_unused2.w = spin dash / peelout charge, v_unused3.b = homing used flag

Sonic_CDAction:
		move.w	(v_unused2).w,d0
		beq.w	.checknew
		bmi.w	.peelcharge

.spindashcharge:
		btst	#bitDn,(v_jpadhold2).w
		beq.w	.release_spindash
		move.b	#id_Roll,obAnim(a0)
		move.b	(v_jpadpress2).w,d1
		andi.b	#btnABC,d1
		beq.w	.actiondone
		addi.w	#$180,(v_unused2).w
		cmpi.w	#$A00,(v_unused2).w
		bls.w	.spinsound
		move.w	#$A00,(v_unused2).w
.spinsound:
		move.w	#sfx_Roll,d0
		jsr	(QueueSound2).l
		bra.w	.actiondone

.release_spindash:
		move.w	(v_unused2).w,d1
		clr.w	(v_unused2).w
		bset	#2,obStatus(a0)
		move.b	#sonic_roll_height,obHeight(a0)
		move.b	#sonic_roll_width,obWidth(a0)
		addq.w	#5,obY(a0)
		move.b	#id_Roll,obAnim(a0)
		btst	#0,obStatus(a0)
		beq.w	.spindashright
		neg.w	d1
.spindashright:
		move.w	d1,obInertia(a0)
		move.w	d1,obVelX(a0)
		move.w	#0,obVelY(a0)
		move.w	#sfx_Roll,d0
		jsr	(QueueSound2).l
		bra.w	.actiondone

.peelcharge:
		btst	#bitUp,(v_jpadhold2).w
		beq.w	.release_peelout
		move.b	(v_jpadhold2).w,d1
		andi.b	#btnABC,d1
		beq.w	.release_peelout
		move.b	#id_Run,obAnim(a0)
		subi.w	#$80,(v_unused2).w
		cmpi.w	#-$C00,(v_unused2).w
		bge.w	.actiondone
		move.w	#-$C00,(v_unused2).w
		bra.w	.actiondone

.release_peelout:
		move.w	(v_unused2).w,d1
		neg.w	d1
		clr.w	(v_unused2).w
		move.b	#id_Run,obAnim(a0)
		btst	#0,obStatus(a0)
		beq.w	.peelright
		neg.w	d1
.peelright:
		move.w	d1,obInertia(a0)
		move.w	d1,obVelX(a0)
		move.w	#0,obVelY(a0)
		move.w	#sfx_Roll,d0
		jsr	(QueueSound2).l
		bra.w	.actiondone

.checknew:
		tst.w	obInertia(a0)
		bne.w	.noaction
		btst	#bitDn,(v_jpadhold2).w
		beq.w	.checkpeelout
		move.b	(v_jpadpress2).w,d1
		andi.b	#btnABC,d1
		beq.w	.noaction
		move.w	#$300,(v_unused2).w
		move.b	#id_Roll,obAnim(a0)
		move.w	#sfx_Roll,d0
		jsr	(QueueSound2).l
		bra.w	.actiondone

.checkpeelout:
		btst	#bitUp,(v_jpadhold2).w
		beq.w	.noaction
		move.b	(v_jpadhold2).w,d1
		andi.b	#btnABC,d1
		beq.w	.noaction
		move.w	#-$300,(v_unused2).w
		move.b	#id_Run,obAnim(a0)
		bra.w	.actiondone
.noaction:
		moveq	#0,d0
		rts
.actiondone:
		ori.b	#1,ccr
		rts
; End of function Sonic_CDAction

Sonic_HomingAttack:
		tst.b	(v_unused3).w
		bne.w	.return
		move.b	(v_jpadpress2).w,d0
		andi.b	#btnABC,d0
		beq.w	.return
		move.b	#1,(v_unused3).w
		bset	#2,obStatus(a0)
		move.b	#sonic_roll_height,obHeight(a0)
		move.b	#sonic_roll_width,obWidth(a0)
		move.b	#id_Roll,obAnim(a0)
		bsr.w	Sonic_FindHomingTarget
		bne.w	.airdash
		move.w	obX(a1),d0
		sub.w	obX(a0),d0
		bpl.w	.targetright
		move.w	#-$A00,obVelX(a0)
		bra.w	.targety
.targetright:
		move.w	#$A00,obVelX(a0)
.targety:
		move.w	obY(a1),d0
		sub.w	obY(a0),d0
		bpl.w	.targetdown
		move.w	#-$800,obVelY(a0)
		bra.w	.sound
.targetdown:
		move.w	#$800,obVelY(a0)
.sound:
		move.w	#sfx_Jump,d0
		jsr	(QueueSound2).l
.return:
		rts
.airdash:
		btst	#0,obStatus(a0)
		bne.w	.dashleft
		move.w	#$C00,obVelX(a0)
		bra.w	.dashup
.dashleft:
		move.w	#-$C00,obVelX(a0)
.dashup:
		move.w	#-$100,obVelY(a0)
		move.w	#sfx_Jump,d0
		jsr	(QueueSound2).l
		rts
; End of function Sonic_HomingAttack

Sonic_FindHomingTarget:
		lea	(v_lvlobjspace).w,a1
		lea	(v_lvlobjend).w,a2
.loop:
		cmpa.l	a2,a1
		bhs.w	.notfound
		tst.b	obID(a1)
		beq.w	.next
		bsr.w	Sonic_IsHomingTarget
		bne.w	.next
		move.w	obX(a1),d0
		sub.w	obX(a0),d0
		bpl.w	.xpositive
		neg.w	d0
.xpositive:
		cmpi.w	#$C0,d0
		bhi.w	.next
		move.w	obY(a1),d1
		sub.w	obY(a0),d1
		bpl.w	.ypositive
		neg.w	d1
.ypositive:
		cmpi.w	#$A0,d1
		bhi.w	.next
		moveq	#0,d0
		rts
.next:
		adda.w	#object_size,a1
		bra.w	.loop
.notfound:
		moveq	#1,d0
		rts
; End of function Sonic_FindHomingTarget

Sonic_IsHomingTarget:
		move.b	obID(a1),d0
		cmpi.b	#id_Monitor,d0
		beq.w	.yes
		cmpi.b	#id_BallHog,d0
		beq.w	.yes
		cmpi.b	#id_Crabmeat,d0
		beq.w	.yes
		cmpi.b	#id_BuzzBomber,d0
		beq.w	.yes
		cmpi.b	#id_Chopper,d0
		beq.w	.yes
		cmpi.b	#id_Jaws,d0
		beq.w	.yes
		cmpi.b	#id_Burrobot,d0
		beq.w	.yes
		cmpi.b	#id_MotoBug,d0
		beq.w	.yes
		cmpi.b	#id_Newtron,d0
		beq.w	.yes
		cmpi.b	#id_Roller,d0
		beq.w	.yes
		cmpi.b	#id_Yadrin,d0
		beq.w	.yes
		cmpi.b	#id_Basaran,d0
		beq.w	.yes
		cmpi.b	#id_Bomb,d0
		beq.w	.yes
		cmpi.b	#id_Orbinaut,d0
		beq.w	.yes
		cmpi.b	#id_Caterkiller,d0
		beq.w	.yes
		moveq	#1,d0
		rts
.yes:
		moveq	#0,d0
		rts
; End of function Sonic_IsHomingTarget
'''


def append_movement_routines(text: str) -> str:
    if MARKER_OBJ in text:
        return text
    return text.rstrip() + MOVEMENT_ROUTINES + "\n"


def patch_main(text: str) -> str:
    if "Sonic_ExtendedCamera" not in text:
        text = must_replace(text, """Level_DoScroll:
\t\tbsr.w\tDeformLayers\t\t\t; scroll planes and do background deformation
""", """Level_DoScroll:
\t\tbsr.w\tSonic_ExtendedCamera\t\t\t; camera lead at high speed
\t\tbsr.w\tDeformLayers\t\t\t; scroll planes and do background deformation
""", "Level_DoScroll")
        text = must_replace(text, """\t\tmove.w\t#0,(v_jpadhold2).w\t\t; clear button input states for Sonic player object
\t\tmove.w\t#0,(v_jpadhold1).w\t\t; clear actual button input states for controller 1
""", """\t\tmove.w\t#0,(v_jpadhold2).w\t\t; clear button input states for Sonic player object
\t\tmove.w\t#0,(v_jpadhold1).w\t\t; clear actual button input states for controller 1
\t\tclr.w\t(v_unused2).w\t\t\t; clear movement hack charge state
\t\tclr.b\t(v_unused3).w\t\t\t; clear movement hack homing state
""", "movement state clear")
    if MARKER_MAIN not in text:
        routine = r'''
; ===========================================================================
; Rubii extended camera routine

Sonic_ExtendedCamera:
		tst.w	(v_debuguse).w
		bne.s	.return
		move.w	(v_player+obVelX).w,d0
		bpl.s	.rightcheck
		cmpi.w	#-$900,d0
		bgt.s	.return
		move.w	(v_limitleft2).w,d1
		addq.w	#8,d1
		cmp.w	(v_screenposx).w,d1
		bhs.s	.return
		subq.w	#2,(v_screenposx).w
		rts
.rightcheck:
		cmpi.w	#$900,d0
		blt.s	.return
		move.w	(v_limitright2).w,d1
		subi.w	#$140,d1
		cmp.w	(v_screenposx).w,d1
		bls.s	.return
		addq.w	#2,(v_screenposx).w
.return:
		rts
; End of function Sonic_ExtendedCamera

'''
        text = must_replace(text, "; ===========================================================================\n; >>> Misc level logic for specific circumstances\n", routine + "; ===========================================================================\n; >>> Misc level logic for specific circumstances\n", "extended camera routine insertion")
    return text


def main() -> int:
    sonic_obj = append_movement_routines(patch_sonic_modes(remove_speed_caps(read(SONIC_OBJ))))
    write(SONIC_OBJ, sonic_obj)
    write(SONIC_MAIN, patch_main(read(SONIC_MAIN)))
    print("Applied movement hack patches: no speed cap, CD spin dash, peelout, extended camera, homing attack.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"movement patch failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
