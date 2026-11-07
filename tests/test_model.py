import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from montador.model import Store  # noqa: E402


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.s = Store()
        self.root = self.s.create_card(None, "raiz")
        self.a = self.s.create_card(self.root.id, "a", snippet="a")
        self.b = self.s.create_card(self.root.id, "b", snippet="b")
        self.a1 = self.s.create_card(self.a.id, "a1", snippet="a1")

    def test_counts(self):
        self.assertEqual(self.s.direct_count(self.root.id), 2)
        self.assertEqual(self.s.total_count(self.root.id), 3)
        self.assertEqual(self.s.direct_count(self.a.id), 1)
        self.assertEqual(self.s.max_depth(self.root.id), 2)

    def test_study_order_last_added_first(self):
        order = [c.front for c in self.s.study_order(self.root.id)]
        self.assertEqual(order, ["a1", "b", "a", "raiz"])

    def test_delete_subtree(self):
        self.s.delete_subtree(self.a.id)
        self.assertEqual(self.s.total_count(self.root.id), 1)
        self.assertNotIn(self.a1.id, self.s.cards)

    def test_save_load(self):
        path = os.path.join(tempfile.mkdtemp(), "x", "f.json")
        self.s.save(path)
        s2 = Store.load(path)
        self.assertEqual([c.front for c in s2.study_order(self.root.id)], ["a1", "b", "a", "raiz"])
        c = s2.create_card(self.root.id)
        self.assertGreater(c.seq, self.a1.seq)


if __name__ == "__main__":
    unittest.main()
