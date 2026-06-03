import os
import tempfile

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QTabWidget, QToolButton

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


def test_retro_menubar_has_functional_actions():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["APPDATA"] = tempfile.mkdtemp(prefix="ytstudio-test-")
    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    assert set(window.menu_buttons) == {"File", "Edit", "View", "Tools", "Help"}
    assert all(isinstance(button, QToolButton) for button in window.menu_buttons.values())

    file_actions = [action.text().replace("&", "") for action in window.menu_buttons["File"].menu().actions()]
    assert "Fetch Info" in file_actions
    assert "Download Now" in file_actions
    assert "Exit" in file_actions

    view_actions = {action.text().replace("&", ""): action for action in window.menu_buttons["View"].menu().actions()}
    view_actions["History"].trigger()
    assert window.screen_stack.currentIndex() == 2
    assert window.status_left.text() == "HISTORY LOG"
