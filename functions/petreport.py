"""petreport — standalone FDG-PET SUVR report for MICA-PET BIDS derivatives.

Generates a single self-contained HTML report per subject/session with five
sections: History, Overview, Volume, Surface, Discussion.

Public API
----------
    from petreport import report
    report(bids_root, subject="sub-PX296", session="ses-01") -> Path

CLI
---
    pip install -e code/                   installs the `petreport` command
    petreport [BIDS_ROOT]                  interactive wizard (default: cwd)

Requires numpy, nibabel, Pillow and questionary; wb_command is optional and
gives per-subject inflated surfaces where it is installed.
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime
import html
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# Configuration
# =============================================================================

ASSETS = Path(__file__).resolve().parents[1] / "resources" / "petreport_assets"

PET_DERIV_GLOB = "MICA-PET*"
RESOLUTION = "fsLR-32k"
N_VERTS = 32492
TRACER = "FDG"

# PET values come from MICA-PET; the hippocampal geometry they sit on comes
# from HippUnfold's own derivative tree.
HIPP_DERIV_GLOB = "hippunfold*"
HIPP_DENSITY = "2mm"

DEFAULT_PVC = "RBV-FS"
DEFAULT_REF = "pons"
DEFAULT_SMOOTH = "10mm"
SMOOTH_LEVELS = ("none", "5mm", "10mm")

WEBP_QUALITY = 89

# Overlay alpha ramps with intensity rather than being flat, so white matter
# does not become a solid slab hiding the anatomy: transparent at ALPHA_LO,
# reaching OVERLAY_ALPHA by ALPHA_HI (fractions of the display maximum).
OVERLAY_ALPHA = 0.72
ALPHA_LO = 0.10
ALPHA_HI = 0.45
SUVR_FLOOR = 0.05

# The Volume tab always renders uncorrected SUVR. RBV-FS is defined only inside
# the gtmseg parcels, so over a T1 it shows the segmentation as much as the
# tracer. Surface maps and the region table keep the requested pvc.
VOLUME_PVC = "none"

UNDERLAY_WITH_SKULL = False
HEAD_FLOOR = 0.15               # head = T1 above this fraction of its 99.5th pct

# 130 Air-Internal, 165 Skull, 257 CSF-ExtraCerebral, 258/259 Head-
# ExtraCerebral. Everything else, pons (174) and vermis (172) included, is brain.
GTMSEG_NONBRAIN = (130, 165, 257, 258, 259)

# 7/46 cerebellar white matter, 8/47 cortex, 172 vermis. The Volume tab drops
# them: they fill the lowest quarter of the axial stack before any cerebrum
# appears. Brainstem (16) and pons (174) — the SUVR reference — stay.
GTMSEG_CEREBELLUM = (7, 8, 46, 47, 172)
VOLUME_SHOW_CEREBELLUM = False

VOLUME_TILE_SCALE = 1.0         # in-plane pixels per voxel in the sprite tiles
VOLUME_BAR_HEIGHT = 72          # height of the bar above the volume stage, px
NAV_LEFT_OFFSET = 8             # horizontal nudge of the topbar nav, px

# Guards against editing a report by accident. Not a security control: it ships
# in the HTML and is readable by anyone who opens the file.
EDIT_PASSCODE = "woof woof"

# Surface viewer camera. CAM_DIST frames the fsLR cortex at CORTEX_RADIUS; any
# other mesh is placed at the same ratio of its own radius, so it fills the
# same share of the viewport.
CAM_DIST = 500.0
CORTEX_RADIUS = 94.0

# Fallback view for a hippocampus with no unfolded surface: from above and
# slightly behind, superior up. Straight down would leave OrbitControls with a
# degenerate azimuth and the surface nearly impossible to turn.
HIPP_VIEW_ELEVATION = 78.0

# Roll of the folded hippocampus about its own long axis, on top of the unfold
# frame. The flat sheet does not take it, so the panel rotates into the page as
# it unrolls.
HIPP_FOLD_ROLL = 0.0

# Turn about the screen's vertical axis, per hemisphere and state. The camera
# cannot do this: it turns fold and sheet together, leaving them in the same
# relation. Where a hemisphere's two entries differ, the panel rotates through
# the difference as it unrolls.
HIPP_VERTICAL_TURN = {
    ("L", "folded"): 45.0,
    ("L", "flat"): 0.0,
    ("R", "folded"): -45.0,
    ("R", "flat"): 0.0,
}

REPORT_FOOTER_ORG = "The Neuro (Montreal Neurological Institute-Hospital) | MICA Lab"


# =============================================================================
# Discovery
# =============================================================================


def find_pet_versions(bids_root: Path) -> list[Path]:
    """Every MICA-PET derivatives directory, oldest name first.

    The dataset can carry more than one pipeline version side by side
    (``MICA-PET_v.alpha.0.6``, ``MICA-PET_v.beta.0.1``), and a subject may
    exist under one but not the other.
    """
    deriv = Path(bids_root) / "derivatives"
    if not deriv.is_dir():
        return []
    return sorted(d for d in deriv.glob(PET_DERIV_GLOB) if d.is_dir())


def find_pet_root(bids_root: Path) -> Optional[Path]:
    """Return the MICA-PET derivatives directory, newest if several."""
    hits = find_pet_versions(bids_root)
    return hits[-1] if hits else None


def find_subjects(pet_root: Path) -> list[str]:
    return sorted(d.name for d in pet_root.iterdir()
                  if d.is_dir() and d.name.startswith("sub-"))


def find_sessions(pet_root: Path, subject: str) -> list[str]:
    sub = pet_root / subject
    return sorted(d.name for d in sub.iterdir()
                  if d.is_dir() and d.name.startswith("ses-"))


def idbids(subject: str, session: Optional[str]) -> str:
    return f"{subject}_{session}" if session else subject


def session_dir(pet_root: Path, subject: str, session: Optional[str]) -> Path:
    return pet_root / subject / session if session else pet_root / subject


# --- file locators ------------------------------------------------------------


def t1_path(sdir: Path, idb: str) -> Path:
    """FreeSurfer-space T1 — the volume section underlay."""
    return sdir / "anat" / f"{idb}_space-FS_T1w.nii.gz"


def find_hipp_root(bids_root: Path) -> Optional[Path]:
    """HippUnfold's derivative tree, which nests a second ``hippunfold/``."""
    hits = sorted(d for d in (Path(bids_root) / "derivatives").glob(HIPP_DERIV_GLOB)
                  if d.is_dir())
    if not hits:
        return None
    inner = hits[-1] / "hippunfold"
    return inner if inner.is_dir() else hits[-1]


def hipp_geom_path(hipp_root: Path, subject: str, session: Optional[str],
                   hemi: str, space: str = "T1w") -> Path:
    """``space-T1w`` is the folded hippocampus, ``space-unfold`` the flat sheet."""
    return (session_dir(hipp_root, subject, session) / "surf" /
            f"{idbids(subject, session)}_hemi-{hemi}_space-{space}"
            f"_den-{HIPP_DENSITY}_label-hipp_midthickness.surf.gii")


def hipp_map_path(sdir: Path, idb: str, hemi: str, pvc: str, ref: str) -> Path:
    return (sdir / "surf" /
            f"{idb}_hemi-{hemi}_surf-hipp_den-{HIPP_DENSITY}_label-midthickness"
            f"_pvc-{pvc}_ref-{ref}_trc-{TRACER}_pet.func.gii")


def pet_volume_path(sdir: Path, idb: str, pvc: str, ref: str) -> Path:
    return (sdir / "pet" /
            f"{idb}_space-T1wFS_pvc-{pvc}_ref-{ref}_trc-{TRACER}_pet.nii.gz")


def surf_geom_path(sdir: Path, idb: str, hemi: str, label: str) -> Path:
    return (sdir / "surf" /
            f"{idb}_hemi-{hemi}_space-T1wFS_surf-{RESOLUTION}_label-{label}.surf.gii")


def surf_map_path(sdir: Path, idb: str, hemi: str, pvc: str, ref: str,
                  smooth: str) -> Path:
    return (sdir / "surf" /
            f"{idb}_hemi-{hemi}_surf-{RESOLUTION}_label-midthickness_"
            f"pvc-{pvc}_ref-{ref}_smooth-{smooth}_trc-{TRACER}_pet.func.gii")


def qc_map_paths(sdir: Path, idb: str, desc: str, ref: str,
                 prefer_pvc: str) -> Optional[tuple[str, dict]]:
    """Locate a derived ``qc/`` surface map: ``(pvc, {"lh": path|None, ...})``.

    Each map is written for the PVC it was computed from (Z from ``pvc-none``,
    AI from ``pvc-RBV-FS``), which need not be the report's, so the PVC is
    globbed for. ``None`` when neither hemisphere is on disk.
    """
    found: dict[str, dict] = {}
    for hemi, key in (("L", "lh"), ("R", "rh")):
        pattern = (f"{idb}_hemi-{hemi}_surf-{RESOLUTION}_label-midthickness_"
                   f"pvc-*_ref-{ref}_trc-{TRACER}_desc-{desc}_pet.func.gii")
        for p in sorted((sdir / "qc").glob(pattern)):
            pvc = p.name.split("_pvc-")[1].split("_ref-")[0]
            found.setdefault(pvc, {})[key] = p
    if not found:
        return None
    pvc = prefer_pvc if prefer_pvc in found else sorted(found)[0]
    return pvc, {"lh": found[pvc].get("lh"), "rh": found[pvc].get("rh")}


def available_smoothings(sdir: Path, idb: str, pvc: str, ref: str) -> list[str]:
    return [s for s in SMOOTH_LEVELS
            if surf_map_path(sdir, idb, "L", pvc, ref, s).exists()
            and surf_map_path(sdir, idb, "R", pvc, ref, s).exists()]


def available_pvcs(sdir: Path, idb: str, ref: str) -> list[str]:
    return [p for p in ("RBV-FS", "none")
            if pet_volume_path(sdir, idb, p, ref).exists()]


def parcel_stats_path(sdir: Path, idb: str, pvc: str, ref: str) -> Path:
    """micapet's own per-region table, when the pipeline wrote one."""
    return (sdir / "qc" /
            f"{idb}_pvc-{pvc}_ref-{ref}_trc-{TRACER}_AI_parcelstats.csv")


def output_dir(sdir: Path) -> Path:
    return sdir / "report"


# =============================================================================
# Asset helpers
# =============================================================================


def _asset_text(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def _png_data_uri(name: str) -> str:
    return ("data:image/png;base64,"
            + base64.b64encode((ASSETS / name).read_bytes()).decode())


def _font_face_css() -> str:
    path = ASSETS / "PlusJakartaSans.ttf"
    if not path.exists():
        return ""
    b64 = base64.b64encode(path.read_bytes()).decode()
    return ("@font-face { font-family: 'Plus Jakarta Sans'; "
            f"src: url('data:font/ttf;base64,{b64}') format('truetype'); "
            "font-weight: 400 700; font-style: normal; font-display: block; }")


def _b64(arr: np.ndarray, dtype) -> str:
    return base64.b64encode(arr.astype(dtype).ravel(order="C").tobytes()).decode()


# =============================================================================
# Surfaces
# =============================================================================


def _load_surf(path: Path) -> tuple[np.ndarray, np.ndarray]:
    gii = nib.load(str(path))
    return (gii.agg_data("pointset").astype(np.float32),
            gii.agg_data("triangle").astype(np.uint32))


def _vertex_normals(coords: np.ndarray, faces: np.ndarray) -> np.ndarray:
    v0, v1, v2 = coords[faces[:, 0]], coords[faces[:, 1]], coords[faces[:, 2]]
    fn = np.cross(v1 - v0, v2 - v0)
    fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
    n = np.zeros_like(coords)
    for i in range(3):
        np.add.at(n, faces[:, i], fn)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return n.astype(np.float32)


def _rigid_transform(source: np.ndarray, target: np.ndarray):
    """Procrustes rigid fit of source onto target.

    Returns an ``apply(points)`` callable so the same transform can be reused
    for the inflated surface; two separately-fitted ones would make the morph
    wobble.
    """
    c_s, c_t = source.mean(axis=0), target.mean(axis=0)
    U, _, Vt = np.linalg.svd((source - c_s).T @ (target - c_t))
    D = np.diag([1.0, 1.0, float(np.sign(np.linalg.det(Vt.T @ U.T)))])
    R = Vt.T @ D @ U.T

    def apply(points: np.ndarray) -> np.ndarray:
        return ((R @ (points - c_s).T).T + c_t).astype(np.float32)

    return apply


def ensure_inflated(sdir: Path, idb: str, hemi: str, cache: Path) -> Path:
    """Return an fsLR-32k inflated surface for this hemisphere.

    Shipped with the dataset if present, else generated from the midthickness
    with wb_command and cached, else the bundled group template.
    """
    shipped = surf_geom_path(sdir, idb, hemi, "inflated")
    if shipped.exists():
        return shipped

    cached = cache / f"{idb}_hemi-{hemi}_{RESOLUTION}_inflated.surf.gii"
    if cached.exists():
        return cached

    wb = shutil.which("wb_command")
    mid = surf_geom_path(sdir, idb, hemi, "midthickness")
    if wb and mid.exists():
        cache.mkdir(parents=True, exist_ok=True)
        very = cache / f"{idb}_hemi-{hemi}_{RESOLUTION}_veryinflated.surf.gii"
        subprocess.run([wb, "-surface-generate-inflated", str(mid),
                        str(cached), str(very), "-iterations-scale", "1.0"],
                       check=True, capture_output=True)
        return cached

    return ASSETS / f"{RESOLUTION}.{hemi}.inflated.surf.gii"


def cortex_mask(hemi: str) -> np.ndarray:
    """uint8 per-vertex mask: 1 = cortex, 0 = medial wall.

    The PET files carry a value at every vertex, medial wall included.
    """
    idx = np.load(ASSETS / f"medial_wall_{RESOLUTION}_{hemi.lower()}h.npy")
    mask = np.ones(N_VERTS, dtype=np.uint8)
    mask[idx.astype(int)] = 0
    return mask


# Derived maps the pipeline writes into qc/. Colormap and range match micapet's
# own plots, so a panel here reads at the same scale as the clinical PNG.
# `threshold` is descriptive only — the pipeline thresholds the Z map before
# writing it, and the value is carried so the sub-label can state it.

# AI is antisymmetric, so one wording covers both hemispheres: the colour
# describes the vertex under the cursor relative to its homologue.
_AI_NOTE_POS = {"text": "Red · higher uptake where you look than in the homologue",
                "cls": "cb-note-pos"}
_AI_NOTE_NEG = {"text": "Blue · lower uptake where you look than in the homologue",
                "cls": "cb-note-neg"}

DERIVED_MAPS = (
    {"desc": "SUVRZscore", "nav_label": "Z-score", "cb_label": "Z",
     "label": "FDG-PET SUVR Z-score", "cmap": "bwr", "vmax": 5.0,
     "threshold": ("|Z|", 1.96), "mirror": False, "clip": None, "cb_note": ()},
    # One panel per sign: the two questions — where is uptake higher than the
    # homologue, where is it lower — are read one at a time. Each keeps its own
    # half of the bwr ramp, so a colour means the same magnitude in both.
    {"desc": "SUVRAI", "nav_label": "Asymmetry +", "cb_label": "Asymmetry",
     "label": "FDG-PET SUVR asymmetry, higher side", "cmap": "bwr", "vmax": 0.25,
     "threshold": None, "mirror": True, "clip": "pos", "cb_note": (_AI_NOTE_POS,)},
    {"desc": "SUVRAI", "nav_label": "Asymmetry −", "cb_label": "Asymmetry",
     "label": "FDG-PET SUVR asymmetry, lower side", "cmap": "bwr", "vmax": 0.25,
     "threshold": None, "mirror": True, "clip": "neg", "cb_note": (_AI_NOTE_NEG,)},
)


def suvr_display_max(sdir: Path, idb: str, pvc: str, ref: str,
                     smooth: str) -> float:
    """The 0..vmax SUVR scale shared by the Volume and Surface tabs.

    The 99th percentile of cortical vertices over both hemispheres. micapet
    uses ``max * 1.5`` instead, which leaves half the colour range unused and
    lets one hot vertex set the scale.
    """
    vals = _load_surf_map({key: surf_map_path(sdir, idb, hemi, pvc, ref, smooth)
                           for hemi, key in (("L", "lh"), ("R", "rh"))})
    both = np.concatenate([vals["lh"], vals["rh"]])
    cortex = np.concatenate([cortex_mask("L"), cortex_mask("R")]).astype(bool)
    finite = both[cortex & np.isfinite(both)]
    return float(np.percentile(finite, 99)) if finite.size else 1.0


def surface_map_specs(sdir: Path, idb: str, pvc: str, ref: str, smooth: str,
                      vmax: float, hipp_root: Optional[Path] = None,
                      subject: str = "", session: Optional[str] = None,
                      log=lambda _msg: None) -> list[dict]:
    """One spec per Surface-tab panel: SUVR, hippocampal SUVR, derived maps.

    Every spec names the mesh it is drawn on. All but the hippocampal one use
    the fsLR-32k cortex.
    """
    specs = [{
        "paths": {h: surf_map_path(sdir, idb, H, pvc, ref, smooth)
                  for H, h in (("L", "lh"), ("R", "rh"))},
        "label": "FDG-PET SUVR",
        "nav_label": "SUVR",
        "sub_label": f"pvc-{pvc} · ref-{ref} · smooth-{smooth}",
        "cb_label": "SUVR",
        "cmap_type": "pos-only",
        "cmap": "jet",
        "vmax": vmax,
        "vmin": 0.0,
        "mirror": False,
        "clip": None,
        "cmap_span": (0.0, 1.0),
        "cb_note": [],
        "mesh": "cortex",
        # Shares its colour range with the hippocampal panel, so rescaling one
        # rescales both and the two stay comparable.
        "scale_group": "suvr",
    }]

    # Hippocampal SUVR, on HippUnfold's midthickness.
    hipp = _hipp_spec(sdir, idb, pvc, ref, vmax, hipp_root, subject, session, log)
    if hipp:
        specs.append(hipp)

    for m in DERIVED_MAPS:
        hit = qc_map_paths(sdir, idb, m["desc"], ref, pvc)
        if hit is None:
            log(f"  {m['nav_label']}: not available")
            continue
        map_pvc, paths = hit
        missing = [h for h, p in paths.items() if p is None]
        if missing:
            sides = ", ".join(HEMI_WORD[h] for h in missing)
            log(f"  {m['nav_label']}: no data for the {sides} hemisphere")
        sub = f"pvc-{map_pvc} · ref-{ref}"
        if m["threshold"]:
            sub += " · {} > {}".format(*m["threshold"])
        # Zero is the colormap midpoint, so a sign-clipped panel takes the
        # half of the ramp on its own side of it: white to red, or blue to
        # white. The full ramp would paint zero-asymmetry cortex deep blue.
        span = {"pos": (0.5, 1.0), "neg": (0.0, 0.5)}.get(m["clip"], (0.0, 1.0))
        specs.append({
            "paths": paths,
            "label": m["label"],
            "nav_label": m["nav_label"],
            "sub_label": sub,
            "cb_label": m["cb_label"],
            "cmap_type": "diverging",
            "cmap": m["cmap"],
            "vmax": 0.0 if m["clip"] == "neg" else m["vmax"],
            "vmin": 0.0 if m["clip"] == "pos" else -m["vmax"],
            "mirror": m["mirror"],
            "clip": m["clip"],
            "cmap_span": span,
            "cb_note": list(m["cb_note"]),
            "mesh": "cortex",
        })
    return specs


def _hipp_spec(sdir: Path, idb: str, pvc: str, ref: str, vmax: float,
               hipp_root: Optional[Path], subject: str, session: Optional[str],
               log) -> Optional[dict]:
    """The hippocampal SUVR panel, or None when either half is missing.

    Needs the PET values (MICA-PET) and the geometry they were sampled on
    (HippUnfold), which live in different derivative trees.
    """
    if hipp_root is None:
        log("  hippocampus: skipped, no HippUnfold data")
        return None
    geom = {h: hipp_geom_path(hipp_root, subject, session, h) for h in ("L", "R")}
    paths = {h: hipp_map_path(sdir, idb, h, pvc, ref) for h in ("L", "R")}
    missing = [p.name for p in list(geom.values()) + list(paths.values())
               if not p.exists()]
    if missing:
        log("  hippocampus: skipped, files missing")
        return None

    # The flattened sheet this panel morphs onto. Same vertex order as the
    # folded surface at the same density, so the values transfer by index —
    # nothing is resampled or smoothed. Without it the panel stays folded.
    flat = {h: hipp_geom_path(hipp_root, subject, session, h, "unfold")
            for h in ("L", "R")}
    if not all(p.exists() for p in flat.values()):
        log("  hippocampus: no unfolded surface, flattening off")
        flat = None

    return {
        "paths": {"lh": paths["L"], "rh": paths["R"]},
        "geom": {"lh": geom["L"], "rh": geom["R"]},
        "geom_flat": {"lh": flat["L"], "rh": flat["R"]} if flat else None,
        "label": "Hippocampal FDG-PET SUVR",
        "nav_label": "SUVR-hipp",
        "sub_label": f"pvc-{pvc} · ref-{ref} · den-{HIPP_DENSITY}",
        "cb_label": "SUVR",
        "cmap_type": "pos-only",
        "cmap": "jet",
        "vmax": vmax,
        "vmin": 0.0,
        "mirror": False,
        "clip": None,
        "cmap_span": (0.0, 1.0),
        "cb_note": [],
        "mesh": "hipp",
        "scale_group": "suvr",
    }


HEMI_WORD = {"lh": "left", "rh": "right"}


def _load_surf_map(paths: dict, mirror: bool = False,
                   log=lambda _msg: None) -> dict:
    """Read one map as {"lh": array, "rh": array}; a blank hemi becomes NaN.

    A hemisphere is blank when its file is absent, or present but identically
    zero — micapet writes the right asymmetry map as a placeholder of zeros,
    which would otherwise render as a genuine finding of no asymmetry.

    With ``mirror`` a blank hemisphere is reconstructed as the negation of the
    other, which is exact for asymmetry (AI_R = -AI_L), then masked by the union
    of both medial walls.
    """
    raw: dict[str, Optional[np.ndarray]] = {}
    for key in ("lh", "rh"):
        p = paths.get(key)
        if p is None:
            raw[key] = None
            continue
        v = np.asarray(nib.load(str(p)).darrays[0].data, dtype=np.float32)
        if len(v) != N_VERTS:
            raise RuntimeError(f"{p.name}: {len(v)} values, expected {N_VERTS}")
        raw[key] = v

    blank = {k: v is None or not np.any(v[np.isfinite(v)]) for k, v in raw.items()}
    vals: dict[str, np.ndarray] = {
        k: (np.full(N_VERTS, np.nan, dtype=np.float32) if blank[k]
            else np.asarray(v, dtype=np.float32))
        for k, v in raw.items()}

    if mirror and sum(blank.values()) == 1:
        dst = "lh" if blank["lh"] else "rh"
        src = "rh" if dst == "lh" else "lh"
        # -vals[src] already carries the donor's wall as NaN; adding the
        # recipient's own wall on top gives the union.
        filled = -vals[src]
        recipient = raw[dst]
        wall = np.isnan(recipient if recipient is not None else vals[src])
        filled[wall] = np.nan
        vals[dst] = filled
    elif any(blank.values()):
        for k, is_blank in blank.items():
            if is_blank and raw[k] is not None:
                log(f"  no data for the {HEMI_WORD[k]} hemisphere")
    return vals


def yale_atlas() -> tuple[dict, list[str]]:
    """Yale-696 parcellation for fsLR-32k: per-hemi vertex→ROI, plus ROI names.

    Label IDs are 1-based; 0 means unassigned. The medial wall is forced to -1
    with the same mask the surface uses, so a vertex carrying no value cannot
    report a parcel name either.
    """
    names = []
    with open(ASSETS / "yale-696_dict.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            names.append(row["Long_name"])

    vtx2roi = {}
    for key in ("lh", "rh"):
        ids = np.asarray(
            nib.load(str(ASSETS / f"yale-696_conte69_{key}.label.gii")).darrays[0].data
        ).astype(np.int32)
        if len(ids) != N_VERTS:
            raise RuntimeError(f"yale-696 {key}: {len(ids)} labels, expected {N_VERTS}")
        roi = np.where(ids > 0, ids - 1, -1).astype(np.int16)
        roi[np.load(ASSETS / f"medial_wall_{RESOLUTION}_{key}.npy").astype(int)] = -1
        vtx2roi[key] = roi
    return vtx2roi, names


def build_surface_payload(sdir: Path, idb: str, specs: list[dict],
                          cache: Path, log=lambda _msg: None) -> dict:
    """Assemble the three.js viewer payload: geometry + one entry per spec."""
    vtx2roi, roi_names = yale_atlas()

    meshes = {"cortex": {}}
    mesh = meshes["cortex"]
    for hemi, key in (("L", "lh"), ("R", "rh")):
        mid_p = surf_geom_path(sdir, idb, hemi, "midthickness")
        mid, faces = _load_surf(mid_p)
        infl, _ = _load_surf(ensure_inflated(sdir, idb, hemi, cache))
        sphere, _ = _load_surf(ASSETS / f"{RESOLUTION}.{hemi}.sphere.surf.gii")

        if len(mid) != N_VERTS or len(infl) != N_VERTS:
            raise RuntimeError(
                f"{hemi}: expected {N_VERTS} vertices, got mid={len(mid)} "
                f"inflated={len(infl)}. Inflated must be resampled to "
                f"{RESOLUTION}, not fsnative.")

        # The subject's surfaces sit in T1wFS scanner space, the templates in
        # canonical fsLR orientation. One rigid fit onto the template
        # midthickness, reused for the inflated surface. The sphere is already
        # a shared fsLR template and needs none.
        tmpl_mid, _ = _load_surf(ASSETS / f"{RESOLUTION}.{hemi}.midthickness.surf.gii")
        to_template = _rigid_transform(mid, tmpl_mid)
        aligned_mid = to_template(mid)
        aligned_infl = to_template(infl)

        mesh[key] = {
            # Lateral view, superior up — the hemisphere's own outer face.
            "view": {"eye": [-1.0, 0.0, 0.0] if key == "lh" else [1.0, 0.0, 0.0],
                     "up": [0.0, 0.0, 1.0]},
            # uint16 is lossless at fsLR-32k (32492 vertices).
            "faces": _b64(faces.ravel(), np.uint16),
            "n_verts": int(N_VERTS),
            "cortex": _b64(cortex_mask(hemi), np.uint8),
            "vertex_to_roi": _b64(vtx2roi[key], np.int16),
            "surfaces": {
                "mid": {"positions": _b64(aligned_mid, np.float16),
                        "normals": _b64(_vertex_normals(aligned_mid, faces), np.float16)},
                "inflated": {"positions": _b64(aligned_infl, np.float16),
                             "normals": _b64(_vertex_normals(aligned_infl, faces), np.float16)},
                "sphere": {"positions": _b64(sphere, np.float16),
                           "normals": _b64(_vertex_normals(sphere, faces), np.float16)},
            },
        }

    # Framing is derived from the cortex and carried to any other mesh by its
    # size — a 35 mm hippocampus at the cortex's distance would be a speck.
    meshes["cortex"]["cam_dist"] = float(CAM_DIST)

    hipp_spec = next((sp for sp in specs if sp["mesh"] == "hipp"), None)
    if hipp_spec is not None:
        meshes["hipp"] = build_hipp_mesh(hipp_spec["geom"], roi_names,
                                         hipp_spec.get("geom_flat"))

    maps = []
    # The two asymmetry panels read the same files; loading once keeps their
    # shared log notes from printing twice.
    loaded: dict[tuple, dict] = {}
    for spec in specs:
        key = (tuple(sorted(map(str, spec["paths"].values()))), spec["mirror"])
        if key not in loaded:
            loaded[key] = (_load_hipp_map(spec["paths"]) if spec["mesh"] == "hipp"
                           else _load_surf_map(spec["paths"], spec["mirror"], log))
        vals = loaded[key]
        # A sign-clipped panel clamps the other half to zero rather than
        # blanking it: zero is the colormap midpoint, so the excluded side
        # renders neutral instead of as thresholded-away grey.
        if spec["clip"]:
            lo, hi = (0.0, None) if spec["clip"] == "pos" else (None, 0.0)
            vals = {k: np.clip(v, lo, hi) for k, v in vals.items()}
        maps.append({
            "label": spec["label"],
            "nav_label": spec["nav_label"],
            "sub_label": spec["sub_label"],
            "cb_label": spec["cb_label"],
            "cmap_type": spec["cmap_type"],
            "cmap": spec["cmap"],
            "cmap_span": list(spec["cmap_span"]),
            "cb_note": spec["cb_note"],
            "vmin": float(spec["vmin"]), "vmax": float(spec["vmax"]),
            "mesh": spec["mesh"],
            "scale_group": spec.get("scale_group"),
            "lh": _b64(vals["lh"], np.float16),
            "rh": _b64(vals["rh"], np.float16),
        })

    return {"meshes": meshes, "maps": maps, "roi_names": roi_names}


def _load_hipp_map(paths: dict) -> dict:
    """Read the hippocampal PET values. Both hemispheres are always written."""
    return {k: np.asarray(nib.load(str(p)).darrays[0].data, dtype=np.float32)
            for k, p in paths.items()}


def _elevated_eye(degrees: float) -> list[float]:
    """Camera direction `degrees` above the horizontal, behind the origin.

    Screen right comes out as patient right and screen up as anterior, matching
    how an axial slice is read.
    """
    rad = np.radians(degrees)
    return [0.0, float(-np.cos(rad)), float(np.sin(rad))]


# Both hippocampal states are built with the head-tail axis on x and the
# sheet's normal on y. A quarter turn about y stands that axis up: the sheet
# ends vertical in the screen plane, anterior at the top, with depth the only
# axis of zero extent. Applied to fold and sheet alike, so the morph between
# them is undisturbed.
_HIPP_TO_SCREEN = np.array([[0.0, 0.0, 1.0],
                            [0.0, 1.0, 0.0],
                            [-1.0, 0.0, 0.0]], np.float32)


def _turn_vertical(degrees: float) -> np.ndarray:
    """Rotation about the screen's vertical axis, positive counter-clockwise
    seen from above. 270 one way is 90 the other, so the sign shows."""
    a = np.radians(degrees)
    return np.array([[np.cos(a), np.sin(a), 0.0],
                     [-np.sin(a), np.cos(a), 0.0],
                     [0.0, 0.0, 1.0]], np.float32)


def _unfold_frame(fold: np.ndarray, flat: np.ndarray) -> np.ndarray:
    """Rotation carrying the folded hippocampus into the flat sheet's frame.

    HippUnfold's unfold space is a parameterisation: its first axis runs head
    to tail, its second across the subfields. Regressing the folded coordinates
    on those two gives the directions they correspond to in the fold, and those
    become the screen axes, so the fold opens onto the sheet without turning.
    """
    centred = flat - flat.mean(axis=0)
    coef, *_ = np.linalg.lstsq(centred[:, :2], fold - fold.mean(axis=0),
                               rcond=None)
    long_ax = coef[0] / np.linalg.norm(coef[0])
    across = coef[1] - (coef[1] @ long_ax) * long_ax
    across /= np.linalg.norm(across)
    depth = np.cross(across, long_ax)
    R = np.column_stack([long_ax, depth, across])
    if np.linalg.det(R) < 0:
        R[:, 1] *= -1
    return R.astype(np.float32)


def build_hipp_mesh(geom: dict, roi_names: list[str],
                    geom_flat: Optional[dict] = None) -> dict:
    """HippUnfold midthickness, packed like the cortical mesh.

    HippUnfold ships no medial wall and no parcellation, so every vertex counts
    as cortex and the hover query names the structure itself.

    Where the cortex morphs midthickness → inflated → sphere, this panel morphs
    the fold onto HippUnfold's unfolded sheet; both stages land on it, so
    scrolling past flat does nothing. With no unfolded surface all three slots
    hold the fold and the morph is inert.
    """
    roi = len(roi_names)
    roi_names.append("Hippocampus")

    mesh = {}
    radius = 0.0
    for hemi, key in (("L", "lh"), ("R", "rh")):
        verts, faces = _load_surf(geom[key])
        # The sheet lies roughly horizontal, so the cortex's lateral view
        # catches it edge-on; from above, body, head and tail are all visible.
        # Only used when there is nothing to unfold onto.
        view = {"eye": _elevated_eye(HIPP_VIEW_ELEVATION), "up": [0.0, 0.0, 1.0]}

        flat_pos = None
        if geom_flat is not None:
            raw_flat, ffaces = _load_surf(geom_flat[key])
            if len(raw_flat) != len(verts):
                raise RuntimeError(
                    f"hemi-{hemi}: unfolded surface has {len(raw_flat)} vertices "
                    f"against the folded surface's {len(verts)}. Both must be "
                    f"den-{HIPP_DENSITY} for the PET values to carry across.")
            # Unfold space is a rectangle at constant z, ~200 mm off the origin.
            # Centre it — float16 steps in 0.125 mm out there and ripples the
            # grid — then quarter turn about x into the frame above.
            fverts = raw_flat - raw_flat.mean(axis=0)
            fverts = np.column_stack([fverts[:, 0], -fverts[:, 2], fverts[:, 1]])
            fverts = (fverts @ _HIPP_TO_SCREEN
                      @ _turn_vertical(HIPP_VERTICAL_TURN[(hemi, "flat")])
                      ).astype(np.float32)
            radius = max(radius, float(np.linalg.norm(fverts, axis=1).max()))
            flat_pos = {"positions": _b64(fverts, np.float16),
                        "normals": _b64(_vertex_normals(fverts, ffaces),
                                    np.float16)}

            # Start the fold in the sheet's frame so it opens without turning.
            # Rotation only: the anatomy is not deformed and the values never move.
            a = np.radians(HIPP_FOLD_ROLL)
            roll = np.array([[1.0, 0.0, 0.0],
                             [0.0, np.cos(a), np.sin(a)],
                             [0.0, -np.sin(a), np.cos(a)]])
            verts = ((verts - verts.mean(axis=0))
                     @ _unfold_frame(verts, raw_flat)
                     @ roll @ _HIPP_TO_SCREEN
                     @ _turn_vertical(HIPP_VERTICAL_TURN[(hemi, "folded")])
                     ).astype(np.float32)

            # The hemispheres are seen from opposite sides of the sheet, so the
            # subfield axis runs opposite ways across the two canvases and the
            # pair reads as the mirror image it anatomically is. three.js flips
            # the normal on a back face, so either side is lit.
            view = {"eye": [0.0, -1.0 if hemi == "L" else 1.0, 0.0],
                    "up": [0.0, 0.0, 1.0]}

        centred = verts - verts.mean(axis=0)
        radius = max(radius, float(np.linalg.norm(centred, axis=1).max()))
        one = {"positions": _b64(verts, np.float16),
               "normals": _b64(_vertex_normals(verts, faces), np.float16)}
        flat = flat_pos if flat_pos is not None else one

        mesh[key] = {
            "view": view,
            "faces": _b64(faces.ravel(), np.uint16),
            "n_verts": int(len(verts)),
            "cortex": _b64(np.ones(len(verts), np.uint8), np.uint8),
            "vertex_to_roi": _b64(np.full(len(verts), roi, np.int16), np.int16),
            "surfaces": {"mid": one, "inflated": flat, "sphere": flat},
        }

    # Same fraction of the viewport as the cortex gets, scaled by size.
    mesh["cam_dist"] = float(CAM_DIST * radius / CORTEX_RADIUS)
    return mesh


def build_surface_html(payload: dict, title: str, table_html: str = "") -> str:
    """Render the YBA viewer into a sandboxed iframe for the Surface tab."""
    doc = _asset_text("template.html")
    doc = (doc
           .replace("{{TITLE}}", html.escape(title))
           .replace("{{FONT_FACE_CSS}}", _font_face_css())
           .replace("{{THEME_CLASS}}", "theme-white")
           .replace("{{THREE_JS}}", _asset_text("three-r128.min.js"))
           .replace("{{ORBIT_CONTROLS_JS}}", _asset_text("OrbitControls-r128.js"))
           .replace("{{HTML2CANVAS_JS}}", _asset_text("html2canvas-1.4.1.min.js"))
           .replace("{{PAYLOAD_JSON}}", json.dumps(payload))
           .replace("{{TABLE_CSS}}", _asset_text("summary.css") if table_html else "")
           .replace("{{TABLE_HTML}}", table_html)
           .replace("{{VIEWER_JS}}", _asset_text("viewer.js"))
           .replace("{{TABLE_JS}}", _asset_text("summary.js") if table_html else ""))
    return (f'<iframe id="surface-frame" srcdoc="{html.escape(doc, quote=True)}" '
            f'sandbox="allow-scripts allow-same-origin"></iframe>')


# =============================================================================
# Volume
# =============================================================================

# matplotlib's `jet` control points, verbatim: micapet plots every SUVR figure
# with cmap="jet", so the volume ramp has to be that exact colormap.
_JET_SEGMENTS = {
    "red":   [(0.00, 0.0), (0.35, 0.0), (0.66, 1.0), (0.89, 1.0), (1.00, 0.5)],
    "green": [(0.00, 0.0), (0.125, 0.0), (0.375, 1.0), (0.64, 1.0),
              (0.91, 0.0), (1.00, 0.0)],
    "blue":  [(0.00, 0.5), (0.11, 1.0), (0.34, 1.0), (0.65, 0.0), (1.00, 0.0)],
}


def _jet_rgb(t: np.ndarray) -> np.ndarray:
    """Map t in [0,1] to RGB uint8 through matplotlib's jet."""
    t = np.clip(t, 0.0, 1.0)
    chans = [np.interp(t, [p[0] for p in seg], [p[1] for p in seg])
             for seg in _JET_SEGMENTS.values()]
    return np.round(np.stack(chans, axis=-1) * 255).astype(np.uint8)


def _to_ras(img):
    """Reorient to closest-canonical RAS so axis 0=R, 1=A, 2=S."""
    return nib.as_closest_canonical(img)


def _bbox(mask: np.ndarray, margin: int = 4) -> tuple[slice, slice, slice]:
    out = []
    for ax in range(3):
        idx = np.where(mask.any(axis=tuple(a for a in range(3) if a != ax)))[0]
        lo = max(int(idx[0]) - margin, 0)
        hi = min(int(idx[-1]) + margin + 1, mask.shape[ax])
        out.append(slice(lo, hi))
    return tuple(out)


# Per view, which array axis is sliced and how the in-plane axes map to image
# rows and columns. These match VIEW_CFG in volume.js; changing one without the
# other misplaces the crosshair.
#   axi: slice k, col = flip(i), row = flip(j)  -> anterior at top
#   sag: slice i, col = flip(j), row = flip(k)  -> anterior at left
#   cor: slice j, col = flip(i), row = flip(k)  -> superior at top
#
# Radiological: the patient's left is on image right, as in micapet's QC
# mosaic. For neurological, the axi/cor hFlip bits in volume.js must be
# inverted to match.
RADIOLOGICAL = True


def _tile(vol: np.ndarray, view: str, n: int) -> np.ndarray:
    # swapaxes(0,1), not .T: the trailing RGB channel axis must stay put.
    def lr(a):
        return np.fliplr(a) if RADIOLOGICAL else a

    if view == "axi":
        return lr(np.flipud(np.swapaxes(vol[:, :, n], 0, 1)))
    if view == "sag":
        return np.fliplr(np.flipud(np.swapaxes(vol[n, :, :], 0, 1)))
    return lr(np.flipud(np.swapaxes(vol[:, n, :], 0, 1)))


def _montage(vol_rgb: np.ndarray, view: str) -> tuple[Image.Image, int, int]:
    """Lay every slice of one view out as a row-major sprite sheet.

    Tile index == slice index (no padding, no reordering), which is what the
    viewer assumes when it converts a voxel index to a tile.
    """
    n_slices = {"axi": vol_rgb.shape[2], "sag": vol_rgb.shape[0],
                "cor": vol_rgb.shape[1]}[view]
    first = _tile(vol_rgb, view, 0)
    th, tw = first.shape[:2]
    if VOLUME_TILE_SCALE != 1.0:
        tw, th = max(1, round(tw * VOLUME_TILE_SCALE)), max(1, round(th * VOLUME_TILE_SCALE))
    cols = int(np.ceil(np.sqrt(n_slices)))
    rows = int(np.ceil(n_slices / cols))
    sheet = np.zeros((rows * th, cols * tw, 3), dtype=np.uint8)
    for s in range(n_slices):
        r, c = divmod(s, cols)
        tile = _tile(vol_rgb, view, s)
        if tile.shape[:2] != (th, tw):
            tile = np.asarray(Image.fromarray(tile).resize((tw, th), Image.LANCZOS))
        sheet[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = tile
    return Image.fromarray(sheet), cols, rows


def _webp_b64(im: Image.Image, lossless: bool = False) -> str:
    buf = io.BytesIO()
    if lossless:
        im.save(buf, format="WEBP", lossless=True, method=6)
    else:
        im.save(buf, format="WEBP", quality=WEBP_QUALITY, method=6)
    return base64.b64encode(buf.getvalue()).decode()


# Colourbar geometry: a horizontal bar one third of the full width, the range
# numbers flanking it, a title above and the unit label below.
_PBAR_FINAL_WIDTH = 3600
_PBAR_HEIGHT = 80
_PBAR_GAP = 15
_PBAR_BG = "white"
_PBAR_TEXT = "black"
_FONT_PBAR_RANGE = 80
_FONT_PBAR_LABEL = 80
_PBAR_LABEL_GAP = 26      # breathing room between the bar and its unit label


def _pbar_font(size: int):
    for path in ("/System/Library/Fonts/Helvetica.ttc",
                 "/System/Library/Fonts/SFNSMono.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
                 "/usr/share/fonts/TTF/DejaVuSans.ttf"):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _pbar_text(text: str, width: int, height: int, size: int) -> Image.Image:
    img = Image.new("RGB", (width, height), _PBAR_BG)
    ImageDraw.Draw(img).text((width // 2, height // 2), text,
                             fill=_PBAR_TEXT, font=_pbar_font(size), anchor="mm")
    return img


def _colorbar_b64(vmin: float, vmax: float, label: str) -> str:
    W, H = _PBAR_FINAL_WIDTH, _PBAR_HEIGHT
    bar_w = W // 3
    side_pad = (W - bar_w) // 2

    ramp = _jet_rgb(np.linspace(0.0, 1.0, bar_w))[None, :, :]
    bar = Image.fromarray(np.repeat(ramp, H, axis=0))

    font = _pbar_font(_FONT_PBAR_RANGE)
    left = Image.new("RGB", (side_pad, H), _PBAR_BG)
    ImageDraw.Draw(left).text((side_pad - _PBAR_GAP, H // 2), f"{vmin:.2f}",
                              fill=_PBAR_TEXT, font=font, anchor="rm")
    right = Image.new("RGB", (side_pad, H), _PBAR_BG)
    ImageDraw.Draw(right).text((_PBAR_GAP, H // 2), f"{vmax:.2f}",
                               fill=_PBAR_TEXT, font=font, anchor="lm")

    row = Image.new("RGB", (W, H), _PBAR_BG)
    row.paste(left, (0, 0)); row.paste(bar, (side_pad, 0))
    row.paste(right, (side_pad + bar_w, 0))

    parts = [row,
             Image.new("RGB", (W, _PBAR_LABEL_GAP), _PBAR_BG),
             _pbar_text(label, W, H, _FONT_PBAR_LABEL),
             Image.new("RGB", (W, 55), _PBAR_BG)]
    out = Image.new("RGB", (W, sum(p.height for p in parts)), _PBAR_BG)
    y = 0
    for part in parts:
        out.paste(part, (0, y)); y += part.height
    return _webp_b64(out)


def brain_mask(sdir: Path, idb: str, pet: np.ndarray, *,
               cerebellum: bool = True) -> np.ndarray:
    """Boolean brain mask on the RAS grid, for restricting the PET overlay.

    Taken from the GTM segmentation by excluding extracerebral labels rather
    than allow-listing brain ones, which would cut the brainstem and the pons.
    The dataset's ``*_desc-brainmask.nii.gz`` is not a mask despite its name.
    """
    seg_p = sdir / "anat" / f"{idb}_space-T1wFS_desc-gtmseg.nii.gz"
    if seg_p.exists():
        drop = GTMSEG_NONBRAIN if cerebellum else GTMSEG_NONBRAIN + GTMSEG_CEREBELLUM
        seg = np.asarray(_to_ras(nib.load(str(seg_p))).dataobj).astype(np.int32)
        return (seg > 0) & ~np.isin(seg, drop)
    return pet > SUVR_FLOOR


def build_volume_payload(sdir: Path, idb: str, pvc: str, ref: str,
                         vmax: float) -> dict:
    """Composite PET SUVR over the FS-space T1 and emit 3-axis sprite sheets."""
    t1_img = _to_ras(nib.load(str(t1_path(sdir, idb))))
    pet_img = _to_ras(nib.load(str(pet_volume_path(sdir, idb, pvc, ref))))
    t1 = np.asarray(t1_img.dataobj, dtype=np.float32)
    pet = np.asarray(pet_img.dataobj, dtype=np.float32)
    if t1.shape != pet.shape:
        raise RuntimeError(f"T1 {t1.shape} and PET {pet.shape} grids differ")

    brain = brain_mask(sdir, idb, pet, cerebellum=VOLUME_SHOW_CEREBELLUM)
    # With the skull, "shown" is the whole head: a fraction of the robust
    # maximum, so it does not depend on how much empty FOV the scan includes.
    shown = brain
    if UNDERLAY_WITH_SKULL:
        shown = t1 > HEAD_FLOOR * np.percentile(t1, 99.5)

    # Crop to what is displayed; every empty slice costs a full sprite tile.
    box = _bbox(shown)
    t1, pet, brain, shown = t1[box], pet[box], brain[box], shown[box]

    # Underlay: greyscale T1, windowed on the displayed voxels so including the
    # skull does not drag the brain's own contrast down.
    t1 = np.where(shown, t1, 0.0)
    lo, hi = np.percentile(t1[shown], [1, 99]) if shown.any() else (0.0, 1.0)
    grey = np.clip((t1 - lo) / max(hi - lo, 1e-6), 0, 1)
    rgb = (grey[..., None] * 255).astype(np.uint8).repeat(3, axis=-1)
    rgb[~shown] = 255           # white outside the head, not black

    # Overlay: SUVR in jet inside the brain, alpha rising with intensity so the
    # T1 shows through. vmax is the report-wide scale, so a colour here means
    # the same value as on the surface.
    vmax = max(float(vmax), 1e-6)
    norm = np.clip(pet / vmax, 0.0, 1.0)
    alpha = np.clip((norm - ALPHA_LO) / max(ALPHA_HI - ALPHA_LO, 1e-6), 0.0, 1.0)
    alpha = np.where(brain & (pet > SUVR_FLOOR), alpha * OVERLAY_ALPHA, 0.0)
    over = _jet_rgb(norm)
    a = alpha[..., None]
    rgb = (rgb * (1.0 - a) + over * a).astype(np.uint8)

    sprites, views = {}, {}
    for view in ("axi", "sag", "cor"):
        sheet, cols, rows = _montage(rgb, view)
        n_slices = {"axi": rgb.shape[2], "sag": rgb.shape[0], "cor": rgb.shape[1]}[view]
        sprites[view] = _webp_b64(sheet)
        views[view] = {"tile_w": sheet.width // cols, "tile_h": sheet.height // rows,
                       "cols": cols, "rows": rows, "n_slices": n_slices}

    return {
        "sprites": sprites,
        "pbar": _colorbar_b64(0.0, vmax, "SUVR"),
        "meta": {
            "label": f"FDG-PET SUVR · pvc-{pvc} · ref-{ref}",
            "dims": [int(x) for x in rgb.shape[:3]],
            "vmin": 0.0, "vmax": vmax,
            "views": views,
        },
    }


def build_volume_html(payload: dict, note: str) -> str:
    """Volume tab: control bar + the 3-view sprite navigator."""
    # Tied to RADIOLOGICAL so the labels cannot contradict the pixels.
    left_lbl, right_lbl = ("R", "L") if RADIOLOGICAL else ("L", "R")
    stage = (
        '<div class="iv-viewer">'
        f'<div class="iv-label left">{left_lbl}</div>'
        f'<div class="iv-label right">{right_lbl}</div>'
        '<div class="iv-views">'
        + "".join(
            f'<div class="iv-view" id="iv-view-{v}">'
            f'<div class="iv-cbox" id="iv-cbox-{v}">'
            f'<canvas id="iv-canvas-{v}"></canvas></div></div>'
            for v in ("axi", "sag", "cor")
        )
        + '</div>'
        '<div class="iv-pbar-row"><img id="iv-pbar" alt="SUVR colour scale"/></div>'
        '<div class="iv-peak" id="iv-peak"></div>'
        '</div>'
    )
    script = (f'<script>window.PETREPORT_VOLUME = {json.dumps(payload)};</script>'
              f'<script>{_asset_text("volume.js")}</script>')
    return (
        '<div class="report-stats">'
        '<div class="report-stats-bar">'
        f'<div class="stats-note"><div>{html.escape(note)}</div></div>'
        '</div>'
        f'<div class="report-stats-stage">{stage}</div>'
        '</div>' + script
    )


# =============================================================================
# Overview — the pipeline's own QC figures
# =============================================================================

# Rows of (caption, filename stem), in the order micapet's QC report shows
# them; the leading fraction is how much of the section width the row takes.
# The pipeline's regional statistics table is left out — the Surface tab
# carries it, sortable and filterable, behind T.
QC_ROWS = (
    (1.0, (("Cortical FDG SUVR", "SUVR_clin_report"),)),
    (0.3, (("Hippocampal FDG SUVR", "hippunfold_clin_report"),)),
    (1.0, (("Cortical asymmetry", "AI_surface_clin_report_cropped"),
           ("Subcortical asymmetry", "AI_subcortical_clin_report_cropped"),
           ("Hippocampal asymmetry", "AI_hippunfold_clin_report"))),
    (1.0, (("Cortical FDG SUVR Z-score, |Z| > 1.96",
            "FDG_SUVR_plot_Zscore_clin_report"),)),
    (1.0, (("PET-MRI overlay", "SUVR_mosaic_screenshot"),)),
)

# Lossless WEBP holds the figures' small type and thin colour bars exactly, at
# roughly half the PNG size. Above this pixel count — only the PET-MRI mosaic —
# the lossy path saves ~1.7 MB.
QC_LOSSLESS_MAX_PX = 2_000_000

# Margin left around a trimmed figure, as a fraction of its longer side.
QC_TRIM_PAD = 0.02


def _trim_white(im: "Image.Image") -> "Image.Image":
    """Crop a QC figure down to its ink, keeping a thin even margin.

    The pipeline's figures carry different amounts of white around the brain,
    so sizing a row by the file's aspect ratio lines the canvases up and leaves
    the brains at different sizes. Trimming first makes the aspect ratio
    describe the content, so a shared height is a shared content height.
    """
    a = np.asarray(im.convert("RGB"))
    ys, xs = np.where((a < 245).any(axis=2))
    if xs.size == 0:
        return im
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    pad = int(round(QC_TRIM_PAD * max(x1 - x0, y1 - y0)))
    return im.crop((max(x0 - pad, 0), max(y0 - pad, 0),
                    min(x1 + 1 + pad, im.width), min(y1 + 1 + pad, im.height)))


def qc_figure_path(sdir: Path, idb: str, pvc: str, ref: str,
                   stem: str) -> Optional[Path]:
    """Locate one QC figure: most carry the full entity prefix, the Z-score
    plot only the subject and session, so try both."""
    for name in (f"{idb}_pvc-{pvc}_ref-{ref}_trc-{TRACER}_{stem}.png",
                 f"{idb}_{stem}.png"):
        path = sdir / "qc" / name
        if path.exists():
            return path
    return None


def build_overview_html(sdir: Path, idb: str, pvc: str, ref: str) -> str:
    """Lay the QC figures out row by row, each captioned.

    Empty string when the session ships none, which drops the section.
    """
    rows = []
    for width, entries in QC_ROWS:
        figures = []
        for caption, stem in entries:
            path = qc_figure_path(sdir, idb, pvc, ref, stem)
            if path is None:
                continue
            im = Image.open(path).convert("RGB")
            # Only figures sharing a row have to line up; a row of one is
            # left as the pipeline drew it.
            if len(entries) > 1:
                im = _trim_white(im)
            data = _webp_b64(im, lossless=im.width * im.height <= QC_LOSSLESS_MAX_PX)
            # flex-grow proportional to the aspect ratio: widths come out in the
            # same proportion, so every figure in the row ends the same height.
            flex = (f' style="flex:{im.width / im.height:.3f}"'
                    if len(entries) > 1 else "")
            figures.append(
                f'<figure class="qc-figure"{flex}>'
                f'<figcaption>{html.escape(caption)}</figcaption>'
                f'<img src="data:image/webp;base64,{data}" '
                f'alt="{html.escape(caption)}"/>'
                '</figure>')
        if not figures:
            continue
        cls = "qc-row" if width == 1 else "qc-row qc-row--narrow"
        style = f' style="width:{width * 100:.0f}%"' if width < 1 else ""
        rows.append(f'<div class="{cls}"{style}>{"".join(figures)}</div>')

    if not rows:
        return ""
    return "".join(rows)


# =============================================================================
# Editable sections
# =============================================================================

_FORMAT_HINT = ("Bold: Ctrl/Cmd+B · Bullet: start a line with '- ' · "
                "Size: Ctrl/Cmd +/- (0 reset)")


def _editable_field(label: str, placeholder: str, hint: bool = False) -> str:
    hint_html = (f'<div class="field-hint">{html.escape(_FORMAT_HINT)}</div>'
                 if hint else "")
    return ('<div class="clinical-field">'
            f'<h3>{html.escape(label)}</h3>'
            '<div class="clinical-edit clinical-edit--multiline" contenteditable="true" '
            f'data-placeholder="{html.escape(placeholder)}"></div>'
            f'{hint_html}</div>')


# =============================================================================
# Summary
# =============================================================================

# Desikan-Killiany cortical + aseg subcortical labels, as micapet's
# parcel_stats() defines them: 37 regions, without frontal and temporal pole.
# gtmseg carries the same IDs, so the table can be recomputed where no
# aparc+aseg is shipped.
PARCEL_REGIONS = (
    ("Cerebellum-Cortex", 8, 47),
    ("Thalamus", 10, 49),
    ("Caudate", 11, 50),
    ("Putamen", 12, 51),
    ("Hippocampus", 17, 53),
    ("Amygdala", 18, 54),
    ("Caudal-Anterior-Cingulate", 1002, 2002),
    ("Caudal-Middle-Frontal", 1003, 2003),
    ("Cuneus", 1005, 2005),
    ("Entorhinal", 1006, 2006),
    ("Fusiform", 1007, 2007),
    ("Inferior-Parietal", 1008, 2008),
    ("Inferior-Temporal", 1009, 2009),
    ("Isthmus-Cingulate", 1010, 2010),
    ("Lateral-Occipital", 1011, 2011),
    ("Lateral-Orbitofrontal", 1012, 2012),
    ("Lingual", 1013, 2013),
    ("Medial-Orbitofrontal", 1014, 2014),
    ("Middle-Temporal", 1015, 2015),
    ("Parahippocampal", 1016, 2016),
    ("Paracentral", 1017, 2017),
    ("Pars-Opercularis", 1018, 2018),
    ("Pars-Orbitalis", 1019, 2019),
    ("Pars-Triangularis", 1020, 2020),
    ("Pericalcarine", 1021, 2021),
    ("Postcentral", 1022, 2022),
    ("Posterior-Cingulate", 1023, 2023),
    ("Precentral", 1024, 2024),
    ("Precuneus", 1025, 2025),
    ("Rostral-Anterior-Cingulate", 1026, 2026),
    ("Rostral-Middle-Frontal", 1027, 2027),
    ("Superior-Frontal", 1028, 2028),
    ("Superior-Parietal", 1029, 2029),
    ("Superior-Temporal", 1030, 2030),
    ("Supramarginal", 1031, 2031),
    ("Transverse-Temporal", 1034, 2034),
    ("Insula", 1035, 2035),
)


def _asymmetry(left: float, right: float) -> float:
    """AI = (L - R) / mean(L, R), at full precision.

    micapet rounds L and R to 2 dp before dividing, which moves ~1 row in 5.
    Here rounding is display-only.
    """
    mean = (left + right) / 2.0
    return (left - right) / mean if mean else 0.0


def aparc_aseg_path(sdir: Path, idb: str) -> Optional[Path]:
    """FreeSurfer's aparc+aseg for this session, if the dataset ships one.

    Either a BIDS-named copy in ``anat/`` or a FreeSurfer-layout
    ``mri/aparc+aseg.mgz`` beside the session.
    """
    for pattern in ("*aparc*aseg*.nii.gz", "*aparc*aseg*.nii", "*aparc*aseg*.mgz"):
        hits = sorted((sdir / "anat").glob(pattern))
        if hits:
            return hits[0]
    for cand in (sdir / "mri" / "aparc+aseg.mgz",
                 sdir.parent / f"{idb}" / "mri" / "aparc+aseg.mgz"):
        if cand.exists():
            return cand
    return None


def _region_means(seg_img, pet_img) -> tuple[list[dict], list[str]]:
    """Mean SUVR per region over a label volume.

    A segmentation on a different grid from the PET (aparc+aseg is 1 mm
    conformed, the PET 0.8 mm) makes the PET resample onto it with order=0, as
    micapet does; the effect measured on this dataset is ~0.004 SUVR.
    """
    seg = np.asarray(seg_img.dataobj).astype(np.int32)
    if seg.shape != pet_img.shape:
        from nibabel.processing import resample_from_to
        pet_img = resample_from_to(pet_img, seg_img, order=0)
    pet = np.asarray(pet_img.dataobj, dtype=np.float32)

    rows, skipped = [], []
    for name, lid, rid in PARCEL_REGIONS:
        lm, rm = seg == lid, seg == rid
        if not lm.any() or not rm.any():
            skipped.append(name)
            continue
        left, right = float(pet[lm].mean()), float(pet[rm].mean())
        rows.append({"region": name, "l": left, "r": right,
                     "diff": left - right, "ai": _asymmetry(left, right)})
    return rows, skipped


def summary_rows(sdir: Path, idb: str, pvc: str, ref: str,
                 log=lambda _msg: None) -> tuple[list[dict], str]:
    """Per-region SUVR and asymmetry, sorted ascending by AI as micapet does.

    Three sources, best first:

    1. micapet's own ``*_AI_parcelstats.csv`` — matches the pipeline exactly.
    2. ``aparc+aseg`` — micapet's parcellation, so the numbers match to within
       the rounding it applies before dividing.
    3. ``gtmseg`` — always present, but a different segmentation: it redraws the
       cortical ribbon for PVC. Subcortical labels agree to ~0.007 SUVR,
       cortical ones differ by ~0.037, and an atrophic structure ringed by
       low-uptake tissue can differ more.

    Returns ``(rows, provenance)``; rows are empty if no source is available.
    """
    csv_p = parcel_stats_path(sdir, idb, pvc, ref)
    if csv_p.exists():
        rows = []
        for line in csv_p.read_text().splitlines()[1:]:
            f = [c.strip() for c in line.split(",")]
            if len(f) < 5:
                continue
            rows.append({"region": f[0], "l": float(f[1]), "r": float(f[2]),
                         "diff": float(f[3]), "ai": float(f[4])})
        if rows:
            rows.sort(key=lambda r: r["ai"])
            return rows, f"{csv_p.name} (micapet)"

    pet_p = pet_volume_path(sdir, idb, pvc, ref)
    if not pet_p.exists():
        log("  region table skipped, no PET volume")
        return [], ""

    seg_p = aparc_aseg_path(sdir, idb)
    exact = seg_p is not None
    if seg_p is None:
        seg_p = sdir / "anat" / f"{idb}_space-T1wFS_desc-gtmseg.nii.gz"
        if not seg_p.exists():
            log("  region table skipped, no segmentation")
            return [], ""

    rows, skipped = _region_means(nib.load(str(seg_p)), nib.load(str(pet_p)))
    if skipped:
        log(f"  {len(skipped)} region(s) not in the segmentation")
    if not rows:
        log("  region table skipped, no regions found")
        return [], ""
    rows.sort(key=lambda r: r["ai"])
    return rows, (f"computed from {seg_p.name}" if exact
                  else f"approximated from {seg_p.name}")


SUMMARY_COLUMNS = (
    ("region", "Region", False),
    ("l", "L SUVR", True),
    ("r", "R SUVR", True),
    ("diff", "L \u2212 R", True),
    ("ai", "Asymmetry", True),
)


def build_summary_table(rows: list[dict]) -> str:
    """Per-region table markup for the surface viewer's T overlay.

    Lives inside the surface iframe so a keypress can pull it up over the
    brain. Empty string when there is nothing to show, leaving T inert.
    """
    if not rows:
        return ""

    head = "".join(
        f'<th class="{"num" if num else "txt"}" '
        f'data-type="{"num" if num else "txt"}">{lbl}</th>'
        for _key, lbl, num in SUMMARY_COLUMNS)

    body = "".join(
        "<tr>" + "".join(
            f'<td class="txt">{html.escape(r["region"].replace("-", " "))}</td>'
            if key == "region" else
            f'<td class="num" data-v="{r[key]:.6f}">{r[key]:.2f}</td>'
            for key, _lbl, _num in SUMMARY_COLUMNS) + "</tr>"
        for r in rows)

    return (
        '<div id="table-panel" class="table-panel">'
        '<div class="table-bar">'
        '<input id="summary-filter" class="summary-filter" type="search" '
        'placeholder="Filter regions\u2026" aria-label="Filter regions"/>'
        '<span class="summary-count" id="summary-count"></span>'
        '<button class="table-close" id="table-close" title="Close (T)" '
        'aria-label="Close">\u00d7</button>'
        '</div>'
        '<div class="summary-scroll">'
        '<table class="summary-table" id="summary-table">'
        f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
        '</div></div>'
    )


def build_history_html() -> str:
    """Clinical history grid: four rows of two editable fields."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = [
        ("Clinical history", "Enter concise clinical history.",
         "Seizure semiology", "Enter seizure semiology."),
        ("EMU | Ictal findings", "Enter EMU ictal findings.",
         "EMU | Interictal findings", "Enter EMU interictal findings."),
        ("MRI findings", "Enter MRI findings.",
         "EEG findings", "Enter EEG findings."),
        ("Other clinical notes", "Enter other clinical notes.",
         "PET scan notes", "Tracer, dose, uptake time, glycaemia."),
    ]
    body = "".join(
        '<div class="history-row-2">'
        + _editable_field(a, ap, hint=(i == 0))
        + _editable_field(b, bp)
        + '</div>'
        for i, (a, ap, b, bp) in enumerate(rows)
    )
    return (body + '<div class="overview-footer" contenteditable="true">'
            f'Report generated on {now} | {REPORT_FOOTER_ORG}</div>')


def build_discussion_html() -> str:
    return (
        '<div class="history-row-2">'
        + _editable_field("Impression",
                          "Enter detailed interpretation of the SUVR maps.", hint=True)
        + _editable_field("Summary", "Enter concise summary and conclusion.")
        + '</div>'
        '<div class="history-row-2">'
        + _editable_field("Additional comments", "Enter additional comments.")
        + '</div>'
    )


# =============================================================================
# Report shell
# =============================================================================


def render_report(subject: str, session: Optional[str], variant: str,
                  overview_html: str, volume_html: str,
                  surface_html: str) -> str:
    """Assemble the single-page report."""
    subj_label = subject.replace("sub-", "")
    ses_label = f" · {session}" if session else ""
    save_base = f"{subject}{('_' + session) if session else ''}_PET_clinical-report"

    icons = {
        "snap": ('<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z">'
                 '</path><circle cx="12" cy="13" r="4"></circle>'),
        "fs": ('<path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3'
               'M16 21h3a2 2 0 0 0 2-2v-3"/>'),
        "edit": ('<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>'
                 '<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>'),
        "save": ('<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>'
                 '<polyline points="17 21 17 13 7 13 7 21"></polyline>'
                 '<polyline points="7 3 7 8 15 8"></polyline>'),
    }

    def btn(cls, bid, title, path):
        return (f'<button class="action-btn {cls}" id="{bid}" title="{title}">'
                '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
                'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                f'stroke-linejoin="round">{path}</svg></button>')

    tabs = [("history", "History")]
    if overview_html:
        tabs.append(("overview", "Overview"))
    tabs += [("volume", "Volume"), ("surface", "Surface"), ("discussion", "Discussion")]
    nav = "".join(
        f'<button class="nav-btn{" active" if i == 0 else ""}" data-target="{t}">{lbl}</button>'
        for i, (t, lbl) in enumerate(tabs)
    )

    overview_section = (
        '<section class="report-section" id="sec-overview">'
        f'<div class="report-inner">{overview_html}</div>'
        '</section>' if overview_html else "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<title>PET Report - {html.escape(subj_label)} — {html.escape(variant)}</title>
<style>
{_font_face_css()}
{_asset_text("report.css")}
{_asset_text("overview.css")}
/* The topbar's neighbours pad differently (22px on .nav-btn, 8px on
   .action-btn), so the nav needs a small left margin to look centred. */
#nav-menu {{ margin-left: {NAV_LEFT_OFFSET}px; }}
.report-stats-bar {{ min-height: {VOLUME_BAR_HEIGHT}px; }}
</style>
</head>
<body class="view-mode">
<div id="report-canvas">

<div class="report-topbar">
  <div class="topbar-left">
    <img src="{_png_data_uri('logo.png')}" class="report-logo" alt="Neuro Logo" />
    <span class="report-subject">{html.escape(subj_label + ses_label)}</span>
  </div>
  <div id="nav-menu">{nav}</div>
  <div class="topbar-actions">
    {btn("snap-btn", "snapshot-btn", "Download Image Snapshot", icons["snap"])}
    {btn("fs-btn", "fullscreen-btn", "Toggle fullscreen", icons["fs"])}
    {btn("edit-btn", "edit-report-btn", "Edit Report", icons["edit"])}
    {btn("save-btn", "save-report-btn", "Save Report", icons["save"])}
  </div>
</div>

<section class="report-section clinical-editor-section active" id="sec-history">
  <div class="report-inner">{build_history_html()}</div>
</section>

{overview_section}

<section class="report-section report-section--stats" id="sec-volume">
  {volume_html}
</section>

<section class="report-section report-section--surface" id="sec-surface">
  {surface_html}
</section>

<section class="report-section clinical-editor-section" id="sec-discussion">
  <div class="report-inner">{build_discussion_html()}</div>
</section>

<div id="unlock-overlay" class="unlock-overlay">
  <div class="unlock-modal">
    <h3>Enter access code</h3>
    <input type="password" id="unlock-input" autocomplete="off">
  </div>
</div>
</div> <!-- close report-canvas -->

<script>{_asset_text("html2canvas-1.4.1.min.js")}</script>
<script>
{_asset_text("report.js").replace("{{SAVE_BASENAME}}", save_base).replace("{{EDIT_PASSCODE}}", json.dumps(EDIT_PASSCODE))}
</script>
</body>
</html>"""


# =============================================================================
# Public API
# =============================================================================


def report(bids_root, subject: str, session: Optional[str] = None, *,
           pvc: str = DEFAULT_PVC, ref: str = DEFAULT_REF,
           smooth: str = DEFAULT_SMOOTH,
           out_dir: Optional[Path] = None,
           pet_root: Optional[Path] = None,
           verbose: bool = True) -> Path:
    """Build one self-contained HTML report. Returns the written path.

    Parameters
    ----------
    bids_root : BIDS dataset root (contains ``derivatives/``).
    subject   : e.g. ``"sub-PX296"``.
    session   : e.g. ``"ses-01"``; ``None`` for session-less layouts.
    pvc, ref  : partial-volume correction and reference region to report.
    smooth    : surface smoothing level to display ("none", "5mm", "10mm").
    out_dir   : defaults to ``<session dir>/report``.
    pet_root  : MICA-PET pipeline directory; defaults to the newest present.
    """
    def log(msg):
        if verbose:
            print(msg, flush=True)

    bids_root = Path(bids_root)
    if pet_root is None:
        pet_root = find_pet_root(bids_root)
    if pet_root is None:
        raise FileNotFoundError(
            f"No {PET_DERIV_GLOB} directory under {bids_root / 'derivatives'}")

    sdir = session_dir(pet_root, subject, session)
    if not sdir.is_dir():
        raise FileNotFoundError(f"No such subject/session: {sdir}")
    idb = idbids(subject, session)

    have = available_smoothings(sdir, idb, pvc, ref)
    if not have:
        raise FileNotFoundError(
            f"No {RESOLUTION} surface maps for pvc-{pvc} ref-{ref} in {sdir / 'surf'}")
    if smooth not in have:
        raise FileNotFoundError(
            f"smooth-{smooth} not available for pvc-{pvc} ref-{ref}; have: {', '.join(have)}")

    out = Path(out_dir) if out_dir else output_dir(sdir)
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "cache"

    log("Generating report...")

    # One SUVR colour scale for the whole report, so a colour means the same
    # value in the Volume tab as in the Surface tab.
    vmax = suvr_display_max(sdir, idb, pvc, ref, smooth)

    vol_pvc = (VOLUME_PVC if pet_volume_path(sdir, idb, VOLUME_PVC, ref).exists()
               else pvc)
    vol_payload = build_volume_payload(sdir, idb, vol_pvc, ref, vmax)

    specs = surface_map_specs(sdir, idb, pvc, ref, smooth, vmax,
                              find_hipp_root(bids_root), subject, session, log)
    surf_payload = build_surface_payload(sdir, idb, specs, cache, log)

    variant = f"pvc-{pvc} · ref-{ref}"

    rows, _provenance = summary_rows(sdir, idb, pvc, ref, log)

    overview_html = build_overview_html(sdir, idb, pvc, ref)

    html_doc = render_report(
        subject, session, variant, overview_html,
        # The note carries only what distinguishes this panel; its pvc need
        # not be the one in the title.
        build_volume_html(vol_payload, f"pvc-{vol_pvc} · ref-{ref}"),
        build_surface_html(surf_payload, f"{idb} surface",
                           build_summary_table(rows)),
    )

    path = out / f"report_{idb}_pvc-{pvc}_ref-{ref}.html"
    path.write_text(html_doc, encoding="utf-8")
    log(f"✓ {path}  ({path.stat().st_size / 1e6:.1f} MB)")
    return path


# =============================================================================
# CLI
# =============================================================================


def _wizard(bids_root: Path) -> int:
    """Pick a scan interactively, then build its report."""
    if not sys.stdin.isatty():
        print("Error: the picker needs an interactive terminal.\n"
              "       Name the scan instead, e.g.\n"
              "         petreport --subject sub-PX296 --session ses-01")
        return 1
    try:
        import questionary                  # CLI-only dependency
    except ImportError:
        print("Error: the picker needs questionary (pip install questionary).\n"
              "       Or name the scan instead, e.g.\n"
              "         petreport --subject sub-PX296 --session ses-01")
        return 1

    style = questionary.Style([("selected", "noreverse"), ("pointer", ""),
                               ("highlighted", "noreverse"), ("answer", "fg:cyan")])

    def choose(label, choices, default=None):
        """The only choice, announced; otherwise a prompt. None if cancelled."""
        if len(choices) == 1:
            print(f"✓ {label}: {choices[0]}")
            return choices[0]
        return questionary.select(f"{label}:", choices=choices,
                                  default=default, pointer=">", style=style).ask()

    versions = find_pet_versions(bids_root)
    if not versions:
        print(f"Error: no {PET_DERIV_GLOB} under {bids_root / 'derivatives'}")
        return 1
    names = [d.name for d in versions]
    name = choose("MICA-PET version", names, default=names[-1])
    if name is None:
        return 0
    pet_root = versions[names.index(name)]

    subjects = find_subjects(pet_root)
    if not subjects:
        print(f"Error: no subjects in {pet_root}")
        return 1
    subject = choose("Subject", subjects)
    if subject is None:
        return 0

    sessions = find_sessions(pet_root, subject)
    session = choose("Session", sessions) if sessions else None
    if sessions and session is None:
        return 0

    sdir = session_dir(pet_root, subject, session)
    idb = idbids(subject, session)

    pvcs = available_pvcs(sdir, idb, DEFAULT_REF)
    if not pvcs:
        print(f"Error: no PET volumes for ref-{DEFAULT_REF} in {sdir / 'pet'}")
        return 1
    pvc = choose("Partial-volume correction", pvcs)
    if pvc is None:
        return 0

    smooths = available_smoothings(sdir, idb, pvc, DEFAULT_REF)
    smooth = choose("Surface smoothing", smooths) if smooths else DEFAULT_SMOOTH
    if smooths and smooth is None:
        return 0

    report(bids_root, subject, session, pvc=pvc, ref=DEFAULT_REF, smooth=smooth,
           pet_root=pet_root)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="petreport",
        description="Generate an FDG-PET SUVR report from MICA-PET derivatives.")
    p.add_argument("bids_root", nargs="?", default=".",
                   help="BIDS dataset root (default: cwd)")
    p.add_argument("--subject")
    p.add_argument("--session")
    p.add_argument("--pvc", default=DEFAULT_PVC)
    p.add_argument("--smooth", default=DEFAULT_SMOOTH, choices=list(SMOOTH_LEVELS),
                   help="surface smoothing level to display")
    p.add_argument("--ref", default=DEFAULT_REF)
    p.add_argument("--out-dir")
    p.add_argument("--pipeline",
                   help="MICA-PET version directory name "
                        "(default: the newest present)")
    args = p.parse_args(argv)

    root = Path(args.bids_root).resolve()
    pet_root = root / "derivatives" / args.pipeline if args.pipeline else None
    if pet_root is not None and not pet_root.is_dir():
        print(f"Error: no such pipeline directory: {pet_root}")
        return 1
    if args.subject:
        report(root, args.subject, args.session, pvc=args.pvc, ref=args.ref,
               smooth=args.smooth,
               out_dir=Path(args.out_dir) if args.out_dir else None,
               pet_root=pet_root)
        return 0
    return _wizard(root)


if __name__ == "__main__":
    sys.exit(main())
