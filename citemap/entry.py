from typing import Optional
import subprocess
import math
import threading
import sys
import dataclasses
from dataclasses import dataclass, field

# import PIL

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainterPath, QFont, QPixmap
from PyQt5.QtWidgets import (QGraphicsItem, QGraphicsTextItem, QGraphicsPixmapItem,
                             QGraphicsDropShadowEffect)

from .models import xy
from .shape import Ellipse, Rectangle, RoundedRectangle, Circle, Shapes, Shape
from .ss import CachePaperData


@dataclass
class EntryState:
    index: int
    coords: xy
    shape: Shapes
    shape_coords: Optional[tuple[int, int]] = None
    text: str = ""
    hidden: bool = False
    collapsed: bool = True
    hash: str = ""
    side: str = "l"
    # expand 'e' for expand, 't' for toggle, 'd' for disabled
    expand: str = "e"
    color: str = "red"
    pdf: str = ""
    paper_data: Optional[CachePaperData] = None
    family: dict = field(default_factory=dict)
    connections: dict[str, list] = field(default_factory=dict)
    font_attribs: dict = field(default_factory=dict)
    part_expand: dict = field(default_factory=dict)

    def __post_init__(self):
        for k in {"siblings", "parents", "children"}:
            if k not in self.family:
                self.family[k] = []
        for k in {"u", "d", "l", "r"}:
            if k not in self.connections:
                self.connections[k] = []
        if not self.font_attribs:
            self.font_attribs = {'family': 'Calibri', 'point_size': 12}
        if not self.part_expand:
            self.part_expand = {'u': 'e', 'd': 'e', 'l': 'e', 'r': 'e'}

    def __setattr__(self, attr, value):
        _fields = [x.name for x in dataclasses.fields(EntryState)]
        if attr not in _fields:
            raise AttributeError(f"Unknown attribute {attr}")
        if attr == "index":
            if not value:
                raise ValueError("Invalid index")
        if attr == "shape" and not Shapes.has(value):
            raise ValueError("Invalid Shape")
        if attr == "connections":
            if not all(x in ["u", "d", "l", "r"] for x in value.keys()):
                raise AttributeError("Got some unknown connection directions")
        super().__setattr__(attr, value)

    def set_connections(self, connections):
        for direction in ["u", "d", "l", "r"]:
            if direction in connections:
                self.connections[direction].extend(connections[direction])


class Entry(QGraphicsTextItem):
    # Class variables
    _mupdf = None
    _imsize = (16, 16)

    # shape_item is the reference to the item
    # state.shape is the type of shape it is
    # self.item = CustomTextItem(self.text, self.shape)
    # Color of the thought is controlled by the Brush of the shape_item
    def __init__(self, scene, index, text, shape=None, coords=None, group=None, data={},
                 paper_data=None):
        super().__init__(text)
        self._scene = scene
        self.initalize_state(index, shape, coords, text, data)
        self.set_shape()
        self.set_variables()
        self.paper_data = paper_data  # why?
        # print(self.qf.boundingRect(self.text).getRect())
        if not coords:
            return
        else:
            self.draw_entry()

    @property
    def index(self) -> int:
        return self.state.index

    @index.setter
    def index(self, val: int):
        self.state.index = val

    @property
    def color(self) -> str:
        return self.state.color

    @color.setter
    def color(self, val: str):
        self.state.color = val

    @property
    def paper_data(self) -> Optional[CachePaperData]:
        return self.state.paper_data

    @paper_data.setter
    def paper_data(self, val: CachePaperData):
        self.state.paper_data = val

    @property
    def family(self):
        return self.state.family

    @property
    def connections(self):
        return self.state.connections

    def set_shape(self):
        if self.state.shape == Shapes.ellipse:
            self.shape_item: Shape = Ellipse(self, self.state.color)
        elif self.state.shape == Shapes.rectangle:
            self.shape_item = Rectangle(self, self.state.color)
        elif self.state.shape == Shapes.rounded_rectangle:
            self.shape_item = RoundedRectangle(self, self.state.color)
        elif self.state.shape == Shapes.circle:
            self.shape_item = Circle(self, self.state.color)
        else:
            raise AttributeError(f"{self.state.shape} is not a valid shape")

    # def setBrush(self, brush):
    #     self.shape_item.setBrush(brush)

    # def pos(self):
    #     rect_ = super(Thought, self).boundingRect().getRect()
    #     return (super().pos().x() - rect_[2], rect_[0])

    # def setPos(self, pos):
    #     self.shape_item.prepareGeometryChange()
    #     super().setPos(pos[0], pos[1])

    def shape(self):
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def pos(self):
        return self.shape_item.pos()

    # Depending on the direction the thought is added, I only have to
    # change the sign in the thought item
    # width and height are in the bottom right diagonal as positive
    # Assumption is that they're added to the end of the groups
    # which is right and down
    def boundingRect(self):
        # rect_ = super(Thought, self).boundingRect().getRect()
        # if self.state.side == 'left':
        #     return QRectF(rect_[0] - rect_[2], rect_[1], rect_[2], rect_[3])  # only invert x axis
        # elif self.state.side == 'right':
        #     return QRectF(rect_[0], rect_[1], rect_[2], rect_[3])  # normal
        # elif self.state.side == 'up':
        #     return QRectF(rect_[0], rect_[1] - rect_[3], rect_[2], rect_[3])  # only invert y axis
        # elif self.state.side == 'down':
        #     return QRectF(rect_[0], rect_[1], rect_[2], rect_[3])  # normal
        return super().boundingRect()

    def focusInEvent(self, event):
        self._scene.typing = True
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.text = self.toPlainText()
        ts = self.textCursor()
        ts.clearSelection()
        self.setTextCursor(ts)
        self._scene.typing = False
        event.accept()  # super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape or (event.key() == Qt.Key_G and event.modifiers() & Qt.ControlModifier):
            self.setTextInteractionFlags(Qt.NoTextInteraction)
            event.accept()
        else:
            super().keyPressEvent(event)

    def set_editable(self, editable=True):
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus()
        # cursor = self.textCursor()
        # cursor.select(cursor.Document)
        # cursor.movePosition(cursor.End)
        # print(cursor.selection().toPlainText())

    # I'll fix this later
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.set_editable(True)
            event.accept()

    def paint(self, painter, style, widget):
        self.shape_item.prepareGeometryChange()
        # painter.drawRect(self.boundingRect())
        # self.document().drawContents(painter, self.boundingRect())
        # painter.drawText(self.boundingRect(), self.document().toPlainText())
        # self.document().drawContents(painter, self.boundingRect())
        # This works now. After every paint() self._scene is also updated
        super().paint(painter, style, widget)
        self._scene.update()

    def draw_entry(self):
        self.prepareGeometryChange()
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(10)
        self.shape_item.setGraphicsEffect(effect)
        self._scene.addItem(self)
        self._scene.addItem(self.shape_item)
        self.setParentItem(self.shape_item)
        # rect_ = self.boundingRect().getRect()
        # now the entry is simply added on the left of the cursor
        if not self.state.shape_coords:
            if self.state.side == 'l':
                self.shape_item.setPos(self.mapFromScene(self.state.coords.x, self.state.coords.y))
                # self.shape_item.setPos(self.mapFromScene(self.state.coords.x - rect_[2], self.state.coords.y))
            elif self.state.side == 'u':
                self.shape_item.setPos(self.mapFromScene(self.state.coords.x, self.state.coords.y))
                # self.shape_item.setPos(self.mapFromScene(self.state.coords.x, self.state.coords.y - rect_[3]))
            else:
                self.shape_item.setPos(self.mapFromScene(self.state.coords.x, self.state.coords.y))
            self.state.shape_coords = (self.shape_item.pos().x(), self.shape_item.pos().y())
        else:
            self.shape_item.setPos(self.state.shape_coords[0], self.state.shape_coords[1])
        # I can paint this directly on to the ellipse also, I don't know which
        # will be faster, but then I'll have to calculate bbox while clicking
        pix = self.pdf_icon()
        if self.state.shape in {Shapes.rectangle, Shapes.rounded_rectangle}:
            self.icon = QGraphicsPixmapItem(pix, self.shape_item)
            self.icon.setPos(-20, -10)
            # self._scene.addItem(item.icon)
        elif self.state.shape == Shapes.ellipse:
            self.icon = QGraphicsPixmapItem(pix, self.shape_item)
            self.icon.setPos(-16, -16)
        elif self.state.shape == Shapes.circle:
            self.icon = QGraphicsPixmapItem(pix, self.shape_item)
            self.icon.setPos(-8, -24)
        self.handle_icon()
        self.icon.open_pdf = self.open_pdf
        # self.itemChange = self.shape_item_change
        self.setSelected = self.shape_item.setSelected
        self.check_hide(self.state.hidden)
        # self.icon.hoverEnterEvent = self.icon_hover_event
        # self.icon.hoverLeaveEvent = self.icon_hover_event
        # self.icon.mouseReleaseEvent = self.icon_release_event

    def to_pixmap(self):
        self.shape_item.to_pixmap()

    def handle_icon(self):
        if self.pdf:
            self.icon.setCursor(Qt.PointingHandCursor)
        else:
            self.icon.setCursor(Qt.ArrowCursor)

    def pdf_icon(self):
        if self.pdf:
            return self._color_file
        else:
            return self._grey_file

    def set_variables(self):
        # This I'll have to check each time
        # self.selected = self.shape_item.isSelected
        # self.content = self.text
        self.icon = None
        # Right now it's not passing control back to the parent
        # But multiple items move if I do control click
        # self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setDefaultTextColor(Qt.black)
        # self.setFlags(self.flags() | QGraphicsItem.ItemIsSelectable)

        self._color_file = QPixmap('icons/pdf.png').scaled(
            20, 20, aspectRatioMode=Qt.KeepAspectRatioByExpanding, transformMode=Qt.SmoothTransformation)
        self._grey_file = QPixmap('icons/pdfgrey.png').scaled(
            20, 20, aspectRatioMode=Qt.KeepAspectRatioByExpanding, transformMode=Qt.SmoothTransformation)
        self.focus_toggle = False
        self.old_coords = None
        self.insert_dir = 'u'
        # rect = self.shape_item.boundingRect().getRect()
        # Relative coords. left, up, right, down
        # self.shape_item.set_link_coords(
        #     ((rect[0], rect[1] + rect[3]/2), (rect[0] + rect[2]/2, rect[1]),
        #      (rect[0] + rect[2], rect[1]+rect[3]/2), (rect[0] + rect[2]/2, rect[1] + rect[3])))
        # self.nearest_child = {'pos': {'horizontal': None, 'vertical': None},
        # 'neg': {'horizontal': None, 'vertical': None}}

    def serialize(self):
        data = {}
        data['index'] = self.state.index
        data['coords'] = (self.state.coords.x, self.state.coords.y)
        data['shape_coords'] = self.state.shape_coords
        data['text'] = self.state.text
        data['font_attribs'] = self.state.font_attribs
        data['pdf'] = self.pdf
        data['expand'] = self.state.expand
        data['part_expand'] = self.state.part_expand
        data['hidden'] = self.state.hidden
        data['hash'] = self.state.hash
        data['shape'] = self.state.shape
        data['color'] = self.state.color
        data['side'] = self.state.side
        data['paper_data'] = self.state.paper_data

        # set is not serializable for some reason
        # May have to amend this later
        family_dict = {}
        for direction in ['u', 'd', 'l', 'r']:
            if direction in self.family:
                values = family_dict[direction]
                family_dict[direction] = list(values) if isinstance(values, set) else values
        family_dict['parents'] = list(self.family['parents'])
        family_dict['children'] = list(self.family['children'])
        data['family'] = family_dict

        return data

    def set_state_property(self, name: str, value):
        if name == "connections":
            self.state.set_connections(value)
        elif name == "family":
            self.set_family(value)
        elif name == "text":
            self.setPlainText(value)
            self.state.text = value
        else:
            setattr(self.state, name, value)

    @property
    def pdf(self):
        return self.state.pdf.replace('file://', '', 1)\
            if self.state.pdf.startswith('file://') else self.state.pdf

    def initalize_state(self, index: int, shape: Shapes, coords, text: str, data: dict):
        self.state = EntryState(index, xy(coords), shape, text=text,
                                **data)
        print("family", data.get("family", None))
        # set text (I guess)
        self.setPlainText(self.state.text)
        # set font
        font = QFont()
        font.setFamily(self.state.font_attribs['family'])
        font.setPointSize(self.state.font_attribs['point_size'])
        self.setFont(font)
        # something with hidden
        self.old_hidden = self.state.hidden

    def connections_in_direction(self, direction):
        return self.state.connections[direction]

    def add_connection_at_end_in_direction(self, index, direction):
        self.state.connections[direction].append(index)

    def add_connections_at_end_in_direction(self, indices, direction):
        self.state.connections[direction].extend(indices)

    def add_connection_at_beginning_in_direction(self, index, direction):
        self.state.connections[direction].insert(0, index)

    def add_connections_at_beginning_in_direction(self, indices, direction):
        self.state.connections[direction] = [*indices, *self.state.connections[direction]]

    def add_parent(self, index):
        if index not in self.family['parents']:
            self.family['parents'].append(index)

    def add_parents(self, parents):
        for p in parents:
            if p not in self.family['parents']:
                self.family['parents'].append(p)

    def add_child(self, index):
        if index not in self.family["children"]:
            self.family['children'].append(index)

    def add_children(self, children):
        for c in children:
            if c not in self.family['children']:
                self.family['children'].append(c)

    def add_sibling(self, index):
        self.family['siblings'].append(index)

    def add_siblings(self, siblings):
        self.family['siblings'].extend([*siblings])

    def set_family(self, family):
        if "children" in family:
            self.add_children(family["children"])
        if "parents" in family:
            self.add_parents(family["parents"])
        if "siblings" in family:
            self.add_siblings(family["siblings"])

    def toggle_expand(self, expand, direction=None):
        if not direction:
            if expand == 't':
                if self.expand == 'e':
                    self.expand = 'd'
                else:
                    self.expand = 'e'
            else:
                self.expand = expand
            for i in self.part_expand.keys():
                self.part_expand[i] = self.expand
            return self.expand
        else:
            if expand == 't':
                if self.part_expand[direction] == 'e':
                    self.part_expand[direction] = 'd'
                else:
                    self.part_expand[direction] = 'e'
            else:
                self.part_expand[direction] = expand
            return self.part_expand[direction]

    def check_hide(self, hidden):
        # if self.old_hidden != hidden:
        #     self.old_hidden = hidden
        self.state.hidden = hidden
        if self.state.hidden:
            self.hide()
        else:
            self.restore()

    def set_transluscent(self, opacity=0.7):
        self.shape_item.setOpacity(opacity)
        self.icon.setOpacity(opacity)
        self.setOpacity(opacity)

    def set_opaque(self):
        self.shape_item.setOpacity(1.0)
        self.icon.setOpacity(1.0)
        self.setOpacity(1.0)

    def update_parent(self, p_ind):
        pass

    # What about the links in the two functions below?
    # Must handle them
    def hide(self):
        self.setVisible(False)
        self.icon.setVisible(False)
        self.shape_item.setVisible(False)

    def restore(self):
        self.setVisible(True)
        self.icon.setVisible(True)
        self.shape_item.setVisible(True)

    def open_pdf(self):
        if self.pdf:
            self.mupdf = subprocess.Popen(['mupdf', self.pdf])

    def close_pdf(self):
        self.mupdf.kill()
        self.mupdf_lock = False

    def remove(self):
        self._scene.removeItem(self.shape_item)
        self._scene.removeItem(self.icon)
        self._scene.removeItem(self)
