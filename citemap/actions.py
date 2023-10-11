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
    win._view.scene().abort()


def quit(win):
    # Quit the window
    sys.exit(0)


def expand_children(win):
    win._view.scene().expand_children()


def expand_parents(win):
    win._view.scene().expand_parents()


def go_left(win):
    win._view.scene().go_in_direction("l")


def go_right(win):
    win._view.scene().go_in_direction("r")


def go_up(win):
    win._view.scene().go_in_direction("u")


def go_down(win):
    win._view.scene().go_in_direction("d")


def select_next(win):
    win._view.scene().select_next()


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


def contract_entries(win):
    selected = win._view.scene().get_selected()
    win._view.scene().contract_entries(selected)


def expand_entries(win):
    selected = win._view.scene().get_selected()
    win._view.scene().expand_entries(selected)


def toggle_expand_entries(win):
    selected = win._view.scene().get_selected()
    win._view.scene().toggle_expand_entries(selected)
