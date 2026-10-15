"""check.py 的測試：範例圖必須全過；每種違規都要被抓到。

    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "arch-blueprint"
EXAMPLE = SKILL / "assets" / "example-overview.svg"

spec = importlib.util.spec_from_file_location("check", SKILL / "scripts" / "check.py")
check = importlib.util.module_from_spec(spec)
sys.modules["check"] = check
spec.loader.exec_module(check)


def run(svg_text: str) -> check.Report:
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False, encoding="utf-8") as f:
        f.write(svg_text)
        path = Path(f.name)
    try:
        return check.check_svg(path)
    finally:
        path.unlink()


class ExampleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.svg = EXAMPLE.read_text(encoding="utf-8")

    def mutate(self, old: str, new: str) -> check.Report:
        self.assertEqual(self.svg.count(old), 1, f"測試用的片段必須在範例裡恰好出現一次：{old!r}")
        return run(self.svg.replace(old, new))

    def assert_error(self, rep: check.Report, code: str, fragment: str = "") -> None:
        hits = [e for e in rep.errors if e.startswith(f"E-{code}") and fragment in e]
        self.assertTrue(hits, f"預期 E-{code} {fragment!r}，實際：{rep.errors}")

    def test_example_passes(self) -> None:
        rep = check.check_svg(EXAMPLE)
        self.assertEqual(rep.errors, [])
        self.assertEqual(rep.warnings, [])

    def test_foreign_color(self) -> None:
        rep = self.mutate('font-weight="600" fill="#1a1a1a">Browser SPA', 'font-weight="600" fill="#c0392b">Browser SPA')
        self.assert_error(rep, "COLOR")

    def test_gradient_forbidden(self) -> None:
        rep = self.mutate("<defs>", '<defs><linearGradient id="g"><stop stop-color="#000"/></linearGradient>')
        self.assert_error(rep, "COLOR", "linearGradient")

    def test_viewbox_width(self) -> None:
        rep = self.mutate('viewBox="0 0 1200 720"', 'viewBox="0 0 1000 720"')
        self.assert_error(rep, "VIEWBOX")

    def test_missing_title(self) -> None:
        rep = self.mutate('<title id="docsearch-title">DocSearch system overview</title>', "")
        self.assert_error(rep, "A11Y")

    def test_diagonal_edge(self) -> None:
        rep = self.mutate('d="M516,408 H558"', 'd="M516,408 L558,420"')
        self.assert_error(rep, "EDGE", "斜線")

    def test_edge_through_node(self) -> None:
        # 把 Query→Vector 改成從 API Server 正下方一路穿過 Object Storage
        rep = self.mutate('d="M692,440 V562"', 'd="M420,440 V700"')
        self.assert_error(rep, "EDGE", "穿過節點")

    def test_arrow_end_gap(self) -> None:
        rep = self.mutate('d="M420,248 V370"', 'd="M420,248 V376"')
        self.assert_error(rep, "EDGE", "終點距")

    def test_missing_hop_at_crossing(self) -> None:
        rep = self.mutate("H700 a8,8 0 0,0 -16,0 H420", "H420")
        self.assert_error(rep, "EDGE", "交叉但沒有跳線")

    def test_fan_points_too_close(self) -> None:
        rep = self.mutate('d="M628,440 V520 H180 V562"', 'd="M684,440 V520 H180 V562"')
        self.assert_error(rep, "EDGE", "接點只相距")

    def test_text_overflow(self) -> None:
        rep = self.mutate(">Object Storage<", ">Object Storage Service Cluster<")
        self.assert_error(rep, "TEXT", "溢出")

    def test_node_overlap(self) -> None:
        rep = self.mutate('<rect x="324" y="568"', '<rect x="290" y="568"')
        self.assert_error(rep, "NODE", "間距不足")

    def test_zone_padding(self) -> None:
        rep = self.mutate('<rect x="884" y="184"', '<rect x="884" y="130"')
        self.assert_error(rep, "ZONE", "內距不足")

    def test_margin(self) -> None:
        rep = self.mutate('<rect x="60" y="120" width="720"', '<rect x="40" y="120" width="720"')
        self.assert_error(rep, "MARGIN")

    def test_too_many_nodes(self) -> None:
        extra = "".join(
            f'<g class="node" id="x{i}"><rect x="{84 + i * 220}" y="800" width="192" height="64" rx="10" '
            f'fill="#faf8f4" stroke="#1a1a1a"/><text x="140" y="830" font-size="14">n{i}</text></g>'
            for i in range(3)
        )
        rep = self.mutate("</svg>", extra + "</svg>")
        self.assert_error(rep, "COUNT", "節點")

    def test_icon_must_match_library(self) -> None:
        rep = self.mutate('<circle cx="5.5" cy="6.5" r="0.5"/>', '<circle cx="5.5" cy="6.5" r="1.5"/>')
        self.assert_error(rep, "ICON", "與 icon 庫不同")

    def test_unknown_icon(self) -> None:
        rep = self.mutate('href="#icon-sparkle"', 'href="#icon-rocket"')
        self.assert_error(rep, "ICON", "icon-rocket")


class PathParserTests(unittest.TestCase):
    def test_relative_and_arc(self) -> None:
        p = check.parse_path("M10,10 h20 v10 a4,4 0 0,1 8,0 H60")
        self.assertEqual(p.errors, [])
        self.assertEqual(p.start, (10, 10))
        self.assertEqual(p.end, (60, 20))
        self.assertEqual(len(p.arcs), 1)
        self.assertEqual([s.axis for s in p.segs], ["h", "v", "h"])

    def test_rounded_corner_ok_and_bad(self) -> None:
        self.assertEqual(check.parse_path("M0,0 H92 Q100,0 100,8 V50").errors, [])
        self.assertTrue(check.parse_path("M0,0 H92 Q96,4 100,8 V50").errors)

    def test_big_arc_rejected(self) -> None:
        self.assertTrue(check.parse_path("M0,0 a40,40 0 0,1 80,0").errors)


if __name__ == "__main__":
    unittest.main()
