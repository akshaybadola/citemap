import sys

from PyQt5.QtCore import Qt, QPointF, QPoint


def zoom_in(win):
    geom = win.geometry()
    center = QPoint(int((geom.x() - geom.width())/2), int((geom.y() - geom.height())/2))
    win._view.zoom_in(center, center)


def zoom_out(win):
    geom = win.geometry()
    center = QPoint(int((geom.x() - geom.width())/2), int((geom.y() - geom.height())/2))
    win._view.zoom_out(center, center)


def save_file(win):
    # Add code here to zoom out your QGraphicsView
    print('Saving File')


def abort(win):
    # pass abort to children
    print("Abort")


def quit(win):
    # Quit the window
    sys.exit(0)


def expand_children(win):
    win._view.scene().expand_children()


def expand_parents(win):
    win._view.scene().expand_parents()


def go_left(win):
    win._view.scene().cycle_between("horizontal", "l", True)


def go_right(win):
    win._view.scene().cycle_between("horizontal", "r", True)


def go_up(win):
    win._view.scene().cycle_between("vertical", "u", True)


def go_down(win):
    win._view.scene().cycle_between("vertical", "d", True)


def select_all(win):
    win._view.scene().select_all()


def select_parents(win):
    selected = win._view.scene().get_selected()
    win._view.scene().select_parents(selected)


def select_children(win):
    selected = win._view.scene().get_selected()
    win._view.scene().select_children(selected)


def toggle_search(win):
    win._view.scene().search_toggle()
