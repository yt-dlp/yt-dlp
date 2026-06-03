import os
import tempfile

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QTabWidget

from gui.main_window import MainWindow


def test_retro_shell_has_sidebar_screens_without_tabs():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["APPDATA"] = tempfile.mkdtemp(prefix="ytstudio-test-")
    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    assert window.findChild(QTabWidget) is None
    assert window.screen_stack.count() == 4
    assert [button.objectName() for button in window.nav_buttons] == [
        "nav-download",
        "nav-queue",
        "nav-history",
        "nav-config",
    ]
    assert window.status_left.text() == "DOWNLOAD MODE"
