import sys
import warnings
import json

from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QGraphicsView, QGraphicsPixmapItem

from . import ss
from .entry import Entry
from .shape import Shape


class View(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self._scene = scene
        self._isPanning = False
        self._mousePressed = False
        self._mousePressedRight = False
        self._positions = []
        self.setRenderHint(QPainter.Antialiasing)
        # Zoom Factor
        self.zoomInFactor = 1.25
        self.zoomOutFactor = 1 / self.zoomInFactor

    def resizeEvent(self, event):
        self._scene.reposition_status_bar(self.geometry())
        super().resizeEvent(event)

    def dragEnterEvent(self, event):
        accepted = False
        mime = event.mimeData()
        self.dragOver = True
        if mime.hasUrls():
            filepath = str(mime.urls()[0].toString())
            filepath = filepath.replace("file://", "")
            # check if readable json
            try:
                with open(filepath) as f:
                    data = json.load(f)
                self._drag_data = ss.parse_data(data)
                if self._drag_data:
                    accepted = True
                warnings.warn("ADD this file to map")
            except json.JSONDecodeError:
                warnings.warn(f"Could not decode file {filepath} as json")
        event.setAccepted(accepted)
        self.scene().update()

    def dragMoveEvent(self, event):
        pass

    def dragLeaveEvent(self, event):
        self.dragOver = True
        self.update()

    def dropEvent(self, event):
        self.dragOver = True
        self._scene.drag_and_drop(
            event,
            self.mapToScene(event.pos()),
            self._drag_data)

    # All this still doesn't work perfectly but is better
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.ShiftModifier:
            self._mousePressed = True
            self.setCursor(Qt.ClosedHandCursor)
            self._dragPos = event.pos()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._selected = self._scene.get_selected()
            self._mousePressedRight = True
            self._dragPos = self.mapToScene(event.pos())
            if self._selected:
                self._scene.try_attach_children(event, self._selected, 'begin')
            self._positions = [s.pos() for s in self._selected]
            event.accept()
        elif self.itemAt(event.pos()):
            item = self.itemAt(event.pos())
            if isinstance(item, Entry):
                if item.hasFocus():
                    pass
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mousePressedRight:
            print(self.mapToScene(event.pos()), event.pos().x(), event.pos().y(),
                  self._dragPos.x(), self._dragPos.y())
            len(self._positions)
            diff = self.mapToScene(event.pos()) - self._dragPos
            if (self._selected):
                for i, item in enumerate(self._selected):
                    item.setPos(self._positions[i].x() + diff.x(), self._positions[i].y() + diff.y())
                self._scene.try_attach_children(event, None, 'dragging')
            event.accept()
        if self._mousePressed and event.modifiers() & Qt.ShiftModifier:  # and event.button == Qt.LeftButton:
            newPos = event.pos()
            diff = newPos - self._dragPos
            self._dragPos = newPos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, QGraphicsPixmapItem):
            item.open_pdf()
            self._mousePressed = False
        if event.button() == Qt.RightButton and self._mousePressedRight:
            self.scene().clearSelection()
            self._mousePressedRight = False
            # NOTE: Will remap this to something else
            #       self._scene.try_attach_children(event, None, 'end')
            warnings.warn("This was try_attach_children")
        elif event.button() == Qt.LeftButton and event.modifiers() & Qt.ShiftModifier:
            self._mousePressed = False
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            self._mousePressed = False
            super().mouseReleaseEvent(event)
        self._scene.resize_and_update()

    def mouseDoubleClickEvent(self, event):
        """Handle Mouse Double Click

        We simply send the event to Item if it's present. Does nothing otherwise

        Args:
            event: QEvent

        """
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, Shape) or isinstance(item, Entry):
                item.mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        """Override Key release event

        Only panning and movement is handled with Shift+Click.
        Rest are handled via actions

        Args:
            event: QEvent

        """
        if event.key() == Qt.Key_Shift and not self._mousePressed:
            self._isPanning = True
            self.setCursor(Qt.OpenHandCursor)

        super().keyPressEvent(event)
        # if not self._scene.typing:  # All the key events handled by the scene go here
        #     if event.key() == Qt.Key_A and event.modifiers() & Qt.ControlModifier:
        #         self._scene.select_all()
        #     if event.key() == Qt.Key_N and event.modifiers() & Qt.ShiftModifier:  # maybe change this later
        #         selected = self.scene().selectedItems()
        #         self._scene.select_descendants(selected)
        #     # if event.key() == Qt.Key_S:
        #     #     if event.modifiers() & Qt.ControlModifier:
        #     #         self._scene.search_toggle()
        #     #     else:
        #     #         self._scene.save_data()
        #     #     event.accept()
        #     if event.key() == Qt.Key_P or event.key() == Qt.Key_Return:  # open_pdf
        #         items = self.scene().selectedItems()
        #         if len(items) == 1 and (
        #                 isinstance(items[0], Entry) or isinstance(items[0], Shape)):
        #             items[0].open_pdf()
        #             event.accept()
        #         else:
        #             super().keyPressEvent(event)
        #     elif event.key() == Qt.Key_Space and event.modifiers() & Qt.ShiftModifier:  # recursive expansion
        #         self._scene.hide_thoughts(self._scene.get_selected(), 'e', recurse=True)
        #         event.accept()
        #     elif event.key() == Qt.Key_Space:  # expansion
        #         self._scene.hide_thoughts(self._scene.get_selected())
        #         event.accept()
        #     elif event.key() == Qt.Key_I:  # insertion
        #         thoughts = self._scene.get_selected()
        #         if len(thoughts) == 1:
        #             self._scene.add_new_child(thoughts[0])
        #         elif not thoughts:
        #             self._scene.add_thought(QPointF(1.0, 1.0))
        #         event.accept()
        #     elif event.key() == Qt.Key_E:  # set editable
        #         items = self.scene().selectedItems()
        #         if len(items) == 1 and (
        #                 isinstance(items[0], Entry) or isinstance(items[0], Shape)):
        #             items[0].set_editable(True)
        #             event.accept()
        #         else:
        #             super().keyPressEvent(event)
        #     elif event.key() == Qt.Key_D:
        #         thoughts = self._scene.get_selected()
        #         if thoughts:
        #             for t in thoughts:
        #                 if isinstance(t, Entry):
        #                     self._scene.delete_thought(t)
        #                 elif isinstance(t, Shape):
        #                     self._scene.delete_thought(t.text_item)
        # # This is when either the QGraphicsTextItem or the QLineEdit have focus
        # else:
        #     super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        # if any keyrelease happens, remove all arrows
        # Though, this is more of a hack.
        self._scene.remove_arrows()
        if event.key() == Qt.Key_Shift:
            if not self._mousePressed:
                self._isPanning = False
                self.setCursor(Qt.ArrowCursor)
        else:
            super().keyPressEvent(event)

    def zoom_in(self, pos, old_pos):
        zoomFactor = self.zoomInFactor
        self.scale(zoomFactor, zoomFactor)

        # Get the new position
        newPos = self.mapToScene(pos)

        # Move scene to old position
        delta = newPos - old_pos
        self.translate(delta.x(), delta.y())
        self.scene().resize_and_update()

    def zoom_out(self, pos, old_pos):
        zoomFactor = self.zoomOutFactor
        self.scale(zoomFactor, zoomFactor)

        # Get the new position
        newPos = self.mapToScene(pos)

        # Move scene to old position
        delta = newPos - old_pos
        self.translate(delta.x(), delta.y())
        self.scene().resize_and_update()

    def wheelEvent(self, event):
        if event.modifiers() and Qt.ControlModifier:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)
            # Save the scene pos
            old_pos = self.mapToScene(event.pos())

            # Zoom
            if event.angleDelta().y() > 0:
                self.zoom_in(event.pos(), old_pos)
            else:
                self.zoom_out(event.pos(), old_pos)
