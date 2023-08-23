import random
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtWidgets import QApplication

from citemap import shape
from citemap import ss
from main import AppWindow, create_view


def maybe_view_citemap(app, view):
    import os
    if os.environ.get("VIEW_CITEMAP"):
        import sys
        window = AppWindow(view, "Mind Map")
        window.show()
        sys.exit(app.exec_())


def test_add_text_thought(config_dir, cache):
    app = QApplication([])
    view = create_view(None)
    data = [*cache.values()][random.randint(0, len(cache))]
    view._scene.add_entry(paper_data=ss.parse_data(data), pos=QPointF(100, 100),
                          shape=shape.Shapes.rectangle)
    maybe_view_citemap(app, view)
