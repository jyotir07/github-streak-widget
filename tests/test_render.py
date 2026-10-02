import unittest
import xml.etree.ElementTree as ET

from render import render_svg

NS = {"svg": "http://www.w3.org/2000/svg"}
LEVELS = ["NONE"] * 37 + ["FOURTH_QUARTILE"]


def parse(svg):
    return ET.fromstring(svg)


class RenderSvgTest(unittest.TestCase):
    def test_is_valid_svg_with_expected_canvas(self):
        root = parse(render_svg(24, LEVELS))
        self.assertEqual((root.get("width"), root.get("height")), ("1660", "260"))

    def test_shows_streak_number_and_label(self):
        root = parse(render_svg(24, LEVELS))
        number = root.find(".//svg:text[@id='streak']", NS)
        self.assertEqual(number.text, "24")
        self.assertIn("24 day", root.get("aria-label"))

    def test_draws_38_tiles_in_two_rows_oldest_top_left(self):
        tiles = parse(render_svg(24, LEVELS)).findall(".//svg:rect[@class='tile']", NS)
        self.assertEqual(len(tiles), 38)
        self.assertEqual((tiles[0].get("x"), tiles[0].get("y")), ("571", "82"))
        self.assertEqual((tiles[18].get("x"), tiles[18].get("y")), ("1561", "82"))
        self.assertEqual((tiles[37].get("x"), tiles[37].get("y")), ("1561", "136"))

    def test_top_level_tile_glows(self):
        tiles = parse(render_svg(24, LEVELS)).findall(".//svg:rect[@class='tile']", NS)
        self.assertEqual(tiles[37].get("filter"), "url(#glow)")
        self.assertIsNone(tiles[0].get("filter"))

    def test_font_shrinks_for_long_numbers(self):
        def size(streak):
            root = parse(render_svg(streak, LEVELS))
            return int(root.find(".//svg:text[@id='streak']", NS).get("font-size"))

        self.assertEqual(size(7), 128)
        self.assertEqual(size(24), 128)
        self.assertEqual(size(365), 100)
        self.assertEqual(size(1200), 80)

    def test_rejects_wrong_level_count(self):
        with self.assertRaises(ValueError):
            render_svg(1, ["NONE"] * 28)

    def test_rejects_unknown_level(self):
        with self.assertRaises(KeyError):
            render_svg(1, ["NONE"] * 37 + ["BOGUS"])


if __name__ == "__main__":
    unittest.main()
