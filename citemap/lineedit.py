from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit


class LineEdit(QLineEdit):
    def __init__(self, *args):
        super().__init__(*args)
        self.text_dict = {}
        self.twt = None

    def set_mmap(self, mmap):
        self.mmap = mmap

    def update_text(self):
        for k, v in self.mmap.thoughts.items():
            if not self.mmap.thoughts[k].hidden:
                self.text_dict[k] = v.text.lower()
            else:
                self.text_dict[k] = ''

    def highlight(self):
        text = self.text()
        twt = []
        for k, v in self.text_dict.items():
            if text in v:
                twt.append(k)
        self.twt = twt
        self.mmap.highlight(twt)

    def keyPressEvent(self, event):
        if event.key() in {Qt.Key_Escape, Qt.Key_Return} or\
           (event.key() in {Qt.Key_G, Qt.Key_S} and event.modifiers() & Qt.ControlModifier):
            self.mmap.search_toggle()
            event.accept()
        elif event.key() in {Qt.Key_P, Qt.Key_N} and event.modifiers() & Qt.ControlModifier:
            if self.mmap.cycle_items:
                self.mmap.search_cycle(event.key())
            else:
                self.mmap.toggle_search_cycle(self.twt)
        else:
            super().keyPressEvent(event)
            self.mmap.toggle_search_cycle(toggle=False)
            self.highlight()
            event.accept()
