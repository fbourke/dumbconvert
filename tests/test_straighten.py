"""Run with: QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests."""

import unittest

from PySide6.QtCore import QLocale, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from simpleneg.app import LabeledSlider


class StraightenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.control = LabeledSlider("Straighten", -15.0, 15.0, 0.0)
        self.changes = []
        self.control.changed.connect(lambda: self.changes.append(self.control.value()))

    def tearDown(self):
        self.control.close()
        self.control.deleteLater()
        self.app.processEvents()

    def test_manual_entry_commits_on_enter(self):
        editor = self.control.value_input.lineEdit()
        editor.selectAll()
        QTest.keyClicks(editor, "-2.3")
        self.assertEqual(self.changes, [])
        QTest.keyClick(editor, Qt.Key_Return)
        self.assertEqual(self.control.value(), -2.3)
        self.assertEqual(self.control.slider.value(), -23)
        self.assertEqual(self.changes, [-2.3])

    def test_dot_and_comma_both_work_in_any_region(self):
        # Comma regions (Italy, most of Europe) and dot regions (US, UK) alike
        for region in ("it_IT", "de_DE", "en_US", "en_GB"):
            for typed in ("-2.3", "-2,3"):
                with self.subTest(region=region, typed=typed):
                    self.control.value_input.setLocale(QLocale(region))
                    self.control.set_value(0.0)
                    editor = self.control.value_input.lineEdit()
                    editor.selectAll()
                    QTest.keyClicks(editor, typed)
                    QTest.keyClick(editor, Qt.Key_Return)
                    self.assertEqual(self.control.value(), -2.3)

    def test_arrows_step_by_one_tenth(self):
        QTest.keyClick(self.control.value_input, Qt.Key_Up)
        self.assertEqual(self.control.value(), 0.1)
        QTest.keyClick(self.control.value_input, Qt.Key_Down)
        self.assertEqual(self.control.value(), 0.0)
        self.assertEqual(self.changes, [0.1, 0.0])

    def test_slider_and_programmatic_updates_stay_synchronized(self):
        self.control.slider.setValue(37)
        self.assertEqual(self.control.value_input.value(), 3.7)
        self.assertEqual(self.changes, [3.7])
        self.control.set_value(-1.2)
        self.assertEqual(self.control.value_input.value(), -1.2)
        self.assertEqual(self.control.slider.value(), -12)
        self.assertEqual(self.changes, [3.7])
        self.control.set_value(2.4, emit=True)
        self.assertEqual(self.control.value_input.value(), 2.4)
        self.assertEqual(self.changes, [3.7, 2.4])

    def test_bounds_apply_to_both_controls(self):
        for requested, expected in ((100, 15.0), (-100, -15.0)):
            with self.subTest(requested=requested):
                self.control.set_value(requested)
                self.assertEqual(self.control.value(), expected)
                self.assertEqual(self.control.value_input.value(), expected)
                QTest.keyClick(self.control.value_input, Qt.Key_Up if expected > 0 else Qt.Key_Down)
                self.assertEqual(self.control.value(), expected)
        self.assertEqual(self.changes, [])
