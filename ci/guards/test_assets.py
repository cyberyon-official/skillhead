"""Images shipped with the plugin stay light and keep their transparency.

The README shows logo.png at 220 px; 440 px covers high-density screens.
Both images are drawn on GitHub's light and dark themes, so neither may
carry an opaque background (a JPEG cannot).
"""
import unittest

from _repo import ROOT

ASSETS = {"logo.png": 440, ".claude-plugin/icon.png": 512}   # width in px
CEILING = 150 * 1024                                          # bytes


class Assets(unittest.TestCase):
    def test_images_are_light(self):
        for name in ASSETS:
            size = (ROOT / name).stat().st_size
            self.assertLess(size, CEILING, f"{name} is {size // 1024} KB: resize or quantize it")

    def test_images_are_transparent_pngs_at_their_width(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow absent: the size check above still runs")
        for name, width in ASSETS.items():
            with Image.open(ROOT / name) as img:
                self.assertEqual(img.format, "PNG", name)
                self.assertEqual(img.width, width, name)
                alpha = img.convert("RGBA").getchannel("A").getextrema()
                self.assertEqual(alpha[0], 0, f"{name} has no transparent pixel")
        with Image.open(ROOT / ".claude-plugin/icon.png") as icon:
            self.assertEqual(icon.width, icon.height, "the plugin icon is square")


if __name__ == "__main__":
    unittest.main()
