# Animal-behavior rigs and enclosures

Arenas, mazes, head-fixation hardware, spouts and ports, and the extrusion frames that carry them.

## Dimensions come from the protocol, not from this file

Behavioral apparatus dimensions are **not standardised**. They are set by the published protocol
the experiment replicates, and they differ between species, strains, ages, and labs. An
elevated plus maze sized for rats is wrong for mice; an open field sized from one paper will not
reproduce another paper's results.

**Ask which protocol or paper the rig replicates, and take the dimensions from it.** If the user
does not have one, say plainly that the geometry is a design choice affecting comparability, and
get their sign-off on the numbers before modelling. Do not supply "standard" maze dimensions from
memory — there is no such standard, and a plausible-looking wrong number is worse here than an
admitted gap, because it silently breaks comparison with prior work.

What this file does cover is the engineering that is common across rigs.

## Regulatory and welfare context

Any apparatus that contacts animals falls under the institution's approved protocol. Before
fabrication:

- The design must be consistent with the **approved IACUC (or local equivalent) protocol**. A
  geometry change — a narrower arm, a different head-plate, a new restraint — may require an
  amendment. Flag this; it is not the modeller's call to make.
- **Materials must be non-toxic and non-irritant**, including after repeated cleaning.
- No **entrapment or pinch geometry**: no gaps that can catch a limb, tail, or head; no wedge-
  shaped gaps that narrow into a trap. Break sharp edges everywhere an animal can reach.
- Anything load-bearing over an animal needs a real margin, not a printed part at minimum wall.

Raise these actively rather than waiting to be asked.

## Materials and cleaning

This dominates material choice, and it eliminates most of the obvious options:

- **Cleaning agents** are the constraint. Ethanol (70%) crazes many plastics; quaternary ammonium
  and chlorine dioxide disinfectants attack others; autoclaving distorts anything with a low glass
  transition temperature. PLA in particular softens well below autoclave temperature and should be
  treated as single-use.
- **Porosity carries odour.** FDM parts are porous by construction, hold odour cues between
  animals, and need validated cleaning/disinfection; do not assume the layer texture is cleanable. Odour is a genuine confound in behavior work. Prefer
  a non-porous process, or seal the surface, or treat FDM parts as consumable and per-cohort.
- **Chew resistance.** Rodents will chew anything reachable. Printed polymer at an exposed edge
  will be destroyed and, worse, ingested. Put metal, glass, or a hard sacrificial edge wherever an
  animal can bite, and keep printed material out of reach where possible.
- **Uncured resin is cytotoxic and an irritant.** SLA parts that contact animals need a validated material/process for the intended contact, including full post-
  cure and washing; those steps alone do not establish safety. See `references/fabrication-limits.md`.

## Video tracking and optics

Most rigs are recorded, and the geometry either helps or fights the tracking:

- **Contrast**: match the surface to the animal's coat so the tracker can segment it. Matte white
  or light grey floors for dark animals, matte dark for albino. **Matte, not gloss** — specular
  highlights are tracked as objects.
- **Avoid shadow-casting geometry** near the floor. Deep walls at low camera angles create shadow
  bands that trackers segment as the animal.
- **Infrared**: if illumination is IR, remember that many "opaque" black plastics transmit IR, and
  that IR-transparent floors change the apparent image. Verify with the actual camera, not by
  assumption.
- Leave a clear, unobstructed camera line to the whole arena, and model the camera mount as part
  of the rig so the field of view is checked before fabrication, not after.

## T-slot extrusion frames

Most rigs are built on aluminium extrusion. The critical fact: **slot width is not implied by
profile size.**

| Profile | Common slot widths | Typical fastener |
| --- | --- | --- |
| 20 x 20 mm | 5 mm or 6 mm depending on series | M4 or M5 T-nut |
| 30 x 30 mm | 8 mm typical | M6 T-nut |
| 40 x 40 mm | 8 mm or 10 mm depending on series | M6 or M8 T-nut |

A 20 mm profile from one supplier takes a 6 mm slot nut; from another, 5 mm. **Measure the slot,
or get the part number.** A bracket modelled for the wrong slot is scrap.

Design notes:

- Slot the bracket's mounting features along the extrusion axis. That is the whole point of
  extrusion — position is continuously adjustable, and a fixed hole throws that away.
- Extrusion faces are the datum. Design brackets to register flat against a face and, where
  possible, into the slot, so the part cannot rotate under load.
- Printed brackets carrying a camera or a heavy component should be treated as prototypes. Polymer
  creeps under sustained load and the camera will slowly droop out of alignment.

## Head fixation

The highest-consequence geometry in this file, and entirely lab-specific.

- The head-plate or head-post interface must come from the **actual implant** the lab uses, as a
  drawing or a measurement. There is no standard. Get the part.
- The kinematic requirement is to constrain the implant **repeatably and without play**, with
  clamping force that does not deflect the plate. Play translates directly into imaging or
  recording motion artefact.
- Fixation hardware must be **quick to release**, both for routine handling and in an emergency.
- Printed clamps flex. For any part carrying head-fixation load, recommend machined metal and
  present the printed version as a fit-check prototype only. Say this explicitly — it is a welfare
  issue as well as a data-quality one.

## Spouts, ports, and reward delivery

- Spout material must be non-toxic and cleanable; stainless steel tubing is the usual choice, held
  by a printed carrier that never itself contacts the animal's mouth.
- Position is a calibrated experimental variable. Make spout position **adjustable and readable**,
  and record it in the manifest, so it can be reproduced across sessions and animals.
- Model the reward line's dead volume — the delay between valve and spout is an experimental
  parameter. See the dead-volume formula in `references/microfluidics.md`.
- If lick detection is capacitive, keep conductive material away from the sensing element and give
  the wire a defined, strain-relieved route in the model.

## Checks to run

```bash
python scripts/gen.py arena_model.py --outdir out/
python scripts/check.py facts out/arena.step
python scripts/check.py clearance out/arena.step out/camera_mount.step --min 1.0
python scripts/snapshot.py out/arena.step --out out/arena.png
```

Confirm in the snapshot:

1. No gap an animal can get a limb, tail, or head into.
2. All animal-reachable edges broken; no sharp corners.
3. Camera has an unobstructed view of the whole floor.
4. Extrusion mounting features are slotted, and on the faces you can actually reach with a tool.
5. Nothing printed sits where it will be chewed.

## Sources

Deliberately none for dimensions. Arena, maze, and head-fixation geometry must come from the
protocol being replicated or from the physical implant, not from a general reference. The
material, cleaning, tracking, and extrusion guidance above is general engineering practice.

Current welfare guidance: <https://nc3rs.org.uk/3rs-resource-library/evaluating-environmental-enrichment/choosing-appropriate-enrichment>.
This informs material/entrapment review, not protocol-specific apparatus dimensions.
