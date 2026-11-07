import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from montador import anki  # noqa: E402
from montador.model import Store  # noqa: E402

QT_HTML = ('<!DOCTYPE HTML><html><head><style type="text/css">p, li { white-space: pre-wrap; }</style></head>'
           '<body style=" font-family:\'Segoe UI\'; font-size:11.5pt;"><p style=" margin-top:0px; -qt-block-indent:0;">'
           '<span style=" font-weight:700; color:#7c3aed;">Plants</span> use '
           '<a href="hl:abc"><span style=" color:#e11d2e; background-color:rgba(225,29,46,0.15);">chlorophyll</span></a>'
           '<span style=" font-size:16pt; text-decoration: underline; text-decoration-color:#facc15;">!</span></p></body></html>')


class AnkiTest(unittest.TestCase):
    def test_conversion_keeps_formatting(self):
        out = anki.qt_html_to_anki(QT_HTML)
        self.assertIn("font-weight:700; color:#7c3aed", out)
        self.assertIn('class="hl"', out)
        self.assertIn("text-decoration-color:#facc15", out)
        self.assertIn("font-size:16pt", out)
        self.assertNotIn("Segoe", out)
        self.assertNotIn("hl:abc", out)
        self.assertNotIn("<style", out)

    def test_plain_front(self):
        self.assertEqual(anki.qt_html_to_anki("chloro &amp; phyll"), "chloro &amp; phyll")

    def test_order(self):
        s = Store()
        r = s.create_card(None, "raiz")
        a = s.create_card(r.id, "a", snippet="a")
        s.create_card(a.id, "a1", snippet="a1")
        s.create_card(r.id, "b", snippet="b")
        self.assertEqual([c.front for c in anki.ordered_cards(s, r.id, True)], ["b", "a1", "a", "raiz"])
        self.assertEqual([c.front for c in anki.ordered_cards(s, r.id, False)], ["raiz", "a", "a1", "b"])


if __name__ == "__main__":
    unittest.main()
