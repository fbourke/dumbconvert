"""Colour regression: the colours DumbConvert gives the test negatives must not change by accident.

The reference colours are in tests/golden/colours.json. A change that moves a colour by more than
TOLERANCE levels (0..255) fails here. If the change is meant (a better conversion), look at the new
numbers, then write them as the new reference:

    DUMBCONVERT_UPDATE_GOLDEN=1 python -m unittest discover -s tests -p test_colour.py

and say in the pull request why the colours changed.
"""

import json
import os
import unittest
from pathlib import Path


from support import PATCHES, engine, test_file

GOLDEN = Path(__file__).parent / "golden" / "colours.json"
TOLERANCE = 3.0          # levels; small differences between machines and platforms stay under this
UPDATE = bool(os.environ.get("DUMBCONVERT_UPDATE_GOLDEN"))

# name -> (settings, how the test negative was exposed)
CASES = {
    "colour, normal exposure": (dict(), dict(exposure=1.0)),
    "colour, 1 stop under": (dict(), dict(exposure=0.5)),
    "colour, 1 stop over": (dict(), dict(exposure=2.0)),
    "B&W, normal exposure": (dict(grayscale=True), dict(exposure=1.0)),
}
_MARGIN = (0.08, 0.07)   # the film border of support.negative, as a share of the height / width


def patch_colours(settings: dict, film: dict) -> dict:
    f = test_file("colour", dust=False, **film)
    img = engine.preview(f, engine.Settings(**settings), 1200).astype(float)
    h, w = img.shape[:2]
    my, mx = _MARGIN
    ph, pw = 0.18 * (1 - 2 * my) * h, 0.14 * (1 - 2 * mx) * w           # patch size in the picture
    out = {}
    for name, (_, (cx, cy)) in PATCHES.items():
        x = (mx + cx * (1 - 2 * mx)) * w
        y = (my + cy * (1 - 2 * my)) * h
        box = img[int(y - ph * 0.2):int(y + ph * 0.2), int(x - pw * 0.2):int(x + pw * 0.2)]
        out[name] = [round(float(v), 1) for v in box.reshape(-1, 3).mean(0)]
    return out


def _layout(measured: dict) -> str:
    """One patch per line, so a pull request's diff shows which colours moved."""
    cases = []
    for case, patches in measured.items():
        rows = ",\n".join(f'    {json.dumps(n)}: {json.dumps(v)}' for n, v in patches.items())
        cases.append(f'  {json.dumps(case)}: {{\n{rows}\n  }}')
    return "{\n" + ",\n".join(cases) + "\n}\n"


class ColourRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.measured = {case: patch_colours(*args) for case, args in CASES.items()}
        if UPDATE:
            GOLDEN.parent.mkdir(exist_ok=True)
            GOLDEN.write_text(_layout(cls.measured))
        cls.golden = json.loads(GOLDEN.read_text()) if GOLDEN.exists() else None

    def test_colours_match_the_reference(self):
        if self.golden is None:
            self.fail(f"no reference colours yet: run with DUMBCONVERT_UPDATE_GOLDEN=1 to write {GOLDEN.name}")
        for case, patches in self.measured.items():
            for name, rgb in patches.items():
                with self.subTest(case=case, patch=name):
                    ref = self.golden[case][name]
                    diff = max(abs(a - b) for a, b in zip(rgb, ref))
                    self.assertLessEqual(diff, TOLERANCE, f"{case}, {name}: {ref} -> {rgb}")

    def test_greys_stay_grey(self):
        # Not a reference: a check of the conversion itself. Grey patches must come out without a cast.
        for case in ("colour, normal exposure",):
            for name in ("grey_dark", "grey_mid", "grey_light"):
                r, g, b = self.measured[case][name]
                with self.subTest(case=case, patch=name):
                    self.assertLess(max(r, g, b) - min(r, g, b), 12, f"{name} has a colour cast: {(r, g, b)}")


if __name__ == "__main__":
    unittest.main()
