import os
import sys
import argparse
import configparser
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QGraphicsView, QApplication, QMainWindow, QGraphicsScene,
                             QStatusBar, QGridLayout, QAction)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtOpenGL import QGL, QGLWidget, QGLFormat

from citemap import CiteMap, LineEdit, StatusBar, View, AppWindow
from citemap.config import load_config


def create_view(filename):
    """Create the :class:`QGraphicsView` view that'll hold the mind maps

    Args:
        filename: Optional filename to open

    """
    scene = CiteMap(filename=filename)
    view = View(scene)
    view.setCacheMode(view.CacheBackground)
    view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
    view.setViewport(QGLWidget(QGLFormat(QGL.SampleBuffers)))
    view.resize(1200, 800)
    line_edit = LineEdit(view)
    status_bar = QStatusBar(view)
    scene.init_widgets(line_edit, status_bar)
    # view.horizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    # view.verticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    # mindmap.setSceneRect(0, 0, 1200, 800)
    scene.stickyFocus = True
    view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)
    return view


def main():
    default_config_dir = Path.joinpath(Path.home().absolute(), ".mindmap")
    parser = argparse.ArgumentParser(description='Mindmap for documents')
    parser.add_argument("-c", "--config-dir", type=str,
                        default=str(default_config_dir),
                        help="Load the config file from this directory")
    parser.add_argument("--file", "-f", type=str, default="", help="Open this saved file")
    args = parser.parse_args()
    filename = None
    if os.path.exists(args.file):
        print("Opening file: " + args.file)
        if os.path.exists(args.file):
            filename = Path(args.file)
    app = QApplication(sys.argv)
    view = create_view(filename)
    config = load_config("config.yaml")
    window = AppWindow(view, "Mind Map", config)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
