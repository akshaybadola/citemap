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
