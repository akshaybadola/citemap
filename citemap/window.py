from functools import partial

from PyQt5.QtWidgets import QMainWindow, QAction

from . import actions
# from .ss import S2


class AppWindow(QMainWindow):
    def __init__(self, view, title, config):
        super().__init__()
        self._view = view
        self._title = title
        self._actions = {}
        self._config = config
        # self._ss = S2(config.data_dir)
        # view._scene.set_ss(self._ss)
        self.initUI(view)

    def _add_action(self, name, key_seq, func, menu=None):
        self._actions[name] = QAction(name, self)
        if isinstance(key_seq, str):
            self._actions[name].setShortcut(key_seq)
        else:
            self._actions[name].setShortcuts(key_seq)
        self._actions[name].triggered.connect(func)
        self.addAction(self._actions[name])
        # TODO: get some menu given by "menu"
        #       Add the action to specified menubar
        # if self._config.menu_bar and menu:
        #     menubar = self.menuBar()
        #     file_menu = menubar.addMenu('File')
        #     view_menu = menubar.addMenu('View')
        #     view_menu.addAction(zoom_in_action)
        #     view_menu.addAction(zoom_out_action)
        #     file_menu.addAction(save_file_action)

    def initUI(self, view):
        self.setCentralWidget(view)

        for binding in self._config.keybindings:
            action_name = binding.action
            action = getattr(actions, action_name.replace(" ", "_").lower())
            self._add_action(action_name, binding.key, partial(action, self))

        self.setWindowTitle(self._title)
        self.setGeometry(100, 100, 1200, 800)

    @property
    def scene(self):
        return self.view._scene
