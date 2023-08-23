from typing import Optional
import operator
from functools import reduce, partial
import warnings
from dataclasses import dataclass

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem


from .paper import Entry
from .link import Arrow, Link
from .shape import Shape, Shapes
from .io import save_file, load_file
from .util import PathLike
from . import ss


Coord = tuple[int, int]


@dataclass
class xy:
    x: int
    y: int

    def __init__(self, *args):
        if len(args) == 2:
            self.x = args[0]
            self.y = args[1]
        else:
            self.x = args[0][0]
            self.y = args[0][1]


class CiteMap(QGraphicsScene):
    """A scene to hold a mindmap. Scene is separate from the mindmap
    so that a new mindmap can be placed on to it easily if required.

    """

    def __init__(self, filename: Optional[PathLike] = None):
        """Initialize the MindMap Scene

        Args:
            root_dir: Root directory for PDF files
            store_dir: Root directory to store the mindmap state
            filename: Filename to load

        """
        super().__init__()
        self.filename = filename
        self.default_insert_direction = 'u'
        self.direction_map = {"pos": {"horizontal": "r", "vertical": "d"},
                              "neg": {"horizontal": "l", "vertical": "u"},
                              "l": ("neg", "horizontal"),
                              "r": ("pos", "horizontal"),
                              "u": ("neg", "vertical"),
                              "d": ("pos", "vertical"),
                              "horizontal": ("l", "r"), "vertical": ("u", "d")}
        self.inverse_map = {"l": "r", "r": "l", "u": "d", "d": "u",
                            "horizontal": ("u", "d"), "vertical": ("l", "r")}
        self.inverse_orientmap = {"horizontal": "vertical", "vertical": "horizontal",
                                  "l": "vertical", "r": "vertical",
                                  "u": "horizontal", "d": "horizontal"}
        self.orient_map = {"l": "horizontal", "u": "vertical", "r": "horizontal", "d": "vertical"}
        self.direction_map_alt = {"l": {"u", "d", "r"},
                                  "r": {"u", "d", "l"},
                                  "u": {"l", "d", "r"},
                                  "d": {"u", "l", "r"}}
        self.op_map = {"l": (-200, 0), "r": (200, 0), "u": (0, -200), "d": (0, 200)}
        self.movement = None
        self.cycle_index = 0
        self.cycle_items = []
        self.typing = False
        self.toggled_search = False
        self.get_selected = self.selectedItems
        self.transluscent = set()
        self.entries = {}
        self.links = {}
        self.selections = []
        self.cur_index = 0
        self.arrows = []
        self.pix_items = []
        self.node_positions = []
        self.dragging_items = []
        self.target_item = None
        self._paper_metadata_cache = {}

    def set_ss(self, ss):
        self._ss = ss

    def init_widgets(self, search_widget, status_bar):
        self.search_widget = search_widget
        self.search_widget.set_mmap(self)
        self.search_widget.setVisible(False)
        self.status_bar = status_bar
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.setStyleSheet("background-color: white")
        self.status_bar.setVisible(True)
        self.status_bar.show()
        self.status_bar.showMessage("Ready...", 0)

    def resize_and_update(self):
        items_rect = self.itemsBoundingRect()
        scene_rect = self.sceneRect()
        ir_size = items_rect.size()
        sr_size = scene_rect.size()
        print((ir_size.width() * ir_size.height()), (sr_size.width() * sr_size.height()))
        if (ir_size.width() * ir_size.height()) > (sr_size.width() * sr_size.height()):
            self.setSceneRect(items_rect)
        self.update()

    def coord(self, item) -> xy:
        """Return coordinates :class:`xy` for item of supported type

        """
        if isinstance(item, int):
            _xy = self.entries[item].shape_item.pos().x(), self.entries[item].shape_item.pos().y()
        elif isinstance(item, Entry):
            _xy = item.shape_item.pos().x(), item.shape_item.pos().y()
        elif isinstance(item, Shape):
            _xy = item.pos().x(), item.pos().y()
        elif isinstance(item, QPointF):
            _xy = item.x(), item.y()
        elif isinstance(item, tuple):
            _xy = item
        return xy(_xy)

    def links_zvalue(self, t, value=1):
        for k in self.links.keys():
            if t.index in k:
                self.links[k].setZValue(value)

    def cycle_check(self, ind):
        if ind not in self.cycle_items:
            self.toggle_nav_cycle(False)

    def toggle_nav_cycle(self, toggle, movement=None, item_inds=None, direction=None):
        # items are always thoughts
        if toggle and not self.cycle_items and item_inds:
            print(movement)
            current_item = self.selectedItems()[0]  # guaranteed to be one
            if isinstance(current_item, Entry):
                item_index = current_item.index
            else:
                item_index = current_item.text_item.index
            sorted_inds = None
            if movement == 'horizontal':
                sorted_inds = [(ind, self.coord(ind).x) for ind in item_inds
                               if self.entries[ind].isVisible()]
                sorted_inds.sort(key=lambda x: x[1])
                print(sorted_inds)
            elif movement == 'vertical':
                sorted_inds = [(ind, self.coord(ind).y) for ind in item_inds
                               if self.entries[ind].isVisible()]
                sorted_inds.sort(key=lambda x: x[1])
            self.cycle_items = [x[0] for x in sorted_inds]
            self.cycle_index = self.cycle_items.index(item_index)
            self.movement = movement
            if direction:
                self.cycle_between(direction, movement, True)
        elif not toggle and self.cycle_items:
            self.cycle_index = 0
            self.cycle_items = []

    def select_one(self, t_ind):
        if isinstance(t_ind, set):
            e = self.entries[list(t_ind)[0]]
        else:
            e = self.entries[t_ind]
        if e.shape_item.isVisible():
            self.unselect_all()
            e.shape_item.setSelected(True)
            gview = self.views()[0]
            gview.ensureVisible(e.shape_item)

    def fetch_paper_data(self, paper_id):
        metadata = self._ss.get_metadata(paper_id)
        self._paper_metadata_cache[paper_id] = metadata

    def _ensure_paper_metadata(self, entry):
        item = entry.text_item
        if item._paper_data.paperId not in self._paper_metadata_cache:
            self.fetch_paper_data(item._paper_data.paperId)
        metadata = self._paper_metadata_cache[item._paper_data.paperId]
        return metadata

    def ensure_family(self, entry):
        metadata = self._ensure_paper_metadata(entry)
        if metadata:
            if "data" in metadata["citations"]:
                citations = metadata["citations"]["data"]
            else:
                citations = metadata["citations"]
            if "data" in metadata["references"]:
                references = metadata["references"]["data"]
            else:
                references = metadata["references"]
            return citations, references
        return None, None

    def ensure_parents(self, entry):
        citations, references = self.ensure_family(entry)
        if references:
            if not entry.family["parents"]:
                for ent in references:
                    self.add_new_parent(entry, ss.parse_data(ent), direction="u")
        else:
            warnings.warn("No references for entry. Need to fetch")

    def ensure_children(self, entry):
        citations, references = self.ensure_family(entry)
        if citations:
            if not entry.family["children"]:
                for ent in citations:
                    self.add_new_child(entry, ss.parse_data(ent), direction="d")
        else:
            warnings.warn("No citations for entry. Need to fetch")

    def cycle_between(self, direction, movement=None, cycle=False):
        print (self.movement, movement)
        if not self.movement:
            self.movement = movement
            self.cycle_between(direction, movement, cycle=cycle)
        elif self.movement != movement:
            print (self.entries[self.cycle_items[self.cycle_index]].family[direction])
            if 'parent' in self.entries[self.cycle_items[self.cycle_index]].family[direction] or \
               'children' in self.entries[self.cycle_items[self.cycle_index]].family[direction]:
                self.movement = None
                self.cycle_items = []
                self.toggle_nav_cycle(False)
                return direction
            else:
                return
        # self.dir_map[
        else:
            if direction == self.dir_map[self.movement][0]:
                if not cycle:
                    self.cycle_index = max(0, self.cycle_index - 1)
                else:
                    self.cycle_index = (self.cycle_index - 1) % len(self.cycle_items)
            elif direction == self.dir_map[self.movement][1]:
                if not cycle:
                    self.cycle_index = min(len(self.cycle_items) - 1, self.cycle_index + 1)
                else:
                    self.cycle_index = (self.cycle_index + 1) % len(self.cycle_items)
            self.select_one(self.cycle_items[self.cycle_index])
            return None

    def expand_children(self):
        selected = self.get_selected()
        if not len(selected) == 1:
            return

        entry = selected[0]
        self.ensure_children(entry)
        if entry.family["children"]:
            self.select_one(entry.family['children'])
            self.toggle_nav_cycle(False)
            self.toggle_nav_cycle(True, item_inds=entry.family['children'],
                                  movement=self.inverse_orientmap["d"])
        self.resize_and_update()

    def expand_parents(self):
        selected = self.get_selected()
        if not len(selected) == 1:
            return

        entry = selected[0]
        self.ensure_parents(entry)
        if entry.family["parents"]:
            self.select_one(entry.family['parents'])
            self.toggle_nav_cycle(False)
            self.toggle_nav_cycle(True, item_inds=entry.family['parents'],
                                  movement=self.inverse_orientmap["u"])
        self.resize_and_update()

    def partial_expand(self, direction):
        selected = self.get_selected()
        if not len(selected) == 1:
            return

        for entry in selected:
            if isinstance(entry, Shape):
                entry = entry.text_item
            print("part_expand", entry.text, entry.part_expand)
            if 'siblings' in entry.family[direction]:  # or 'siblings' in entry.family[self.inverse_map[direction]]:
                if entry.part_expand[direction] == 'e':
                    if 'children' in entry.family[direction]:  # and entry.family[direction]['children']:
                        self.select_one(entry.family[direction]['children'])
                        self.toggle_nav_cycle(False)
                        self.toggle_nav_cycle(True, item_inds=entry.family[direction]['children'],
                                              movement=self.inverse_orientmap[direction])
                    else:
                        print("not children, collapsing_opposite", direction, entry.part_expand)
                        entry.part_expand[direction] = 'd'
                        self.collapse_indir(entry, self.inverse_map[direction])
                elif 'children' in entry.family[direction]:
                    entry.part_expand[direction] = 'e'
                    self.expand_indir(entry, direction)
                else:
                    entry.part_expand[self.inverse_map[direction]] = 'd'
                    self.collapse_indir(entry, self.inverse_map[direction])
            else:
                if entry.part_expand[self.inverse_map[direction]] == 'e':
                    if 'children' in entry.family[self.inverse_map[direction]]:
                        entry.toggle_expand('d', self.inverse_map[direction])
                        self.collapse_indir(entry, self.inverse_map[direction])
                    else:
                        entry.toggle_expand('e', direction)
                        self.expand_indir(entry, direction)
                else:
                    if 'children' in entry.family[direction]:
                        entry.toggle_expand('e', direction)
                        self.expand_indir(entry, direction)
                    else:
                        entry.part_expand[self.inverse_map[direction]] = 'd'
                        self.collapse_indir(entry, self.inverse_map[direction])

    def dist(self, a, b):
        """Return squared Euclidean distance between two data types
        Overloaded a, b are supported from which x, y coordinates
        can be extracted.

        Args:
            a: Data type a
            b: Data type b


        """
        coord_a, coord_b = self.coord(a), self.coord(b)
        return (coord_a.x - coord_b.x) ** 2 + (coord_a.y - coord_b.y) ** 2

    def reposition_status_bar(self, geom):
        """Reposition status bar on gometry change

        Args:
            geom: geometry


        """
        rect = geom.getRect()
        self.status_bar.setGeometry(0, rect[3] - 40, rect[2], 50)

    def save_data(self, filename=None):
        print("trying to save data")
        self.status_bar.showMessage("trying to save data", 0)
        if not filename:
            filename = '/home/joe/test.json'
        data = {}
        data["entries"] = []
        for t in self.entries.values():
            data["entries"].append(t.serialize())
        data["links"] = list(zip(list(self.links.keys()),
                                 [link.direction for link in self.links.values()]))
        save_file(data, filename)
        self.status_bar.showMessage("Saved to file" + filename, 0)

    def load_data(self, filename=None):
        print("trying to load data")
        if not filename:
            filename = '/home/joe/test.json'
        data = load_file(filename)
        if data == {}:
            return
        for t in data["entries"]:
            self.add_entry(QPointF(t['coords'][0], t['coords'][1]), data=t)
        links_data = data["links"]
        for link in links_data:
            self.add_link(link[0][0], link[0][1], link[1])
        for t in self.entries.keys():
            for lk in self.links.keys():
                if t in lk and self.entries[t].hidden:
                    self.links[lk].setVisible(False)

    def update_pos(self):
        """This method is called via :class:`Shape` if the :class:`Shape` position changes

        """
        for thought in self.entries.values():
            thought.coords = thought.mapToScene(thought.pos())
            thought.shape_coords = (thought.shape_item.pos().x(), thought.shape_item.pos().y())

    def add_entry(self, paper_data: ss.Paper, pos: Coord, data=None, shape=None):
        """Add the given :class:`ss.Paper` entry data at pos

        Args:
            data: Paper data
            pos: Coordinate position
            shape: Optional shape

        """
        if not shape:
            shape = Shapes.rounded_rectangle
        self.cur_index += 1
        self.entries[self.cur_index] = Entry(self, self.cur_index,
                                             text=ss.format_entry(paper_data),
                                             coords=pos, shape=shape,
                                             data=data or {},
                                             paper_data=paper_data)
        self.resize_and_update()

    def update_parent(self, children, target):
        # if there are multiple famillies, find the highest member in each
        # What if I only attach the parent and not the children?
        # Currently it"s assumed that the children move with the parent
        indices = set([child.index for child in children])
        indices_full = indices.copy()
        filtered = [c for c in children]
        ol = len(filtered)

        diff = 1
        while (diff):
            for f in filtered:
                if f.family["parent"] in indices:
                    indices.remove(f.index)
            filtered = list(filter(lambda c: c.index in indices, children))
            diff = ol - len(filtered)
            ol = len(filtered)

        # indices has the top level nodes
        # for each index check parent, children and siblings
        # change parent to target, change children to only those which are in selection
        # change siblings to union which are in selection and children of newly attached parent
        # for those which are not top-level, change siblings and children

        # For each top level node that is attached, attach them in the same direction.
        #  - change the directions of all their children to away from the parent node

        # The direction now is correct w.r.t. the average of the top level nodes
        # I"m not dealing with the old family though.
        # Remove old family, attach to new one
        direction = self.attach_dir(target, indices)
        idir = self.inverse_map[direction]
        for ind in indices:
            t = self.entries[ind]

            # remove from old family
            t_pind = t.family["parent"]
            if t_pind:
                t_par = self.entries[t.family["parent"]]
                d_0, d_1 = self.inverse_map[self.orient_map[t.side]]
                # First remove sibling
                for sib in t_par.family[t.side]["children"]:
                    if "siblings" in self.entries[sib].family[d_0] and\
                       t.index in self.entries[sib].family[d_0]["siblings"]:
                        self.entries[sib].family[d_0]["siblings"].remove(t.index)
                    if "siblings" in self.entries[sib].family[d_1] and\
                       t.index in self.entries[sib].family[d_1]["siblings"]:
                        self.entries[sib].family[d_1]["siblings"].remove(t.index)

                t_par.family["children"].remove(t.index)
                t_par.family[t.side]["children"].remove(t.index)
                self.fix_family(self.entries[sib])
                self.removeItem(self.links[(t_par.index, t.index)])
                self.links.pop((t_par.index, t.index))
            # Add to new family.  At addition the positions of
            # all children of attached nodes should be updated.
            t.family["parent"] = target.index
            t.side = direction
            if "children" in t.family[idir]:
                self.replace_children(t, idir, direction)

            # clean the thought
            for c in ["u", "d", "l", "r"]:
                if "children" in t.family[c] and (c != direction):
                    self.replace_children(t, c, c)
                if "siblings" in t.family[c]:
                    t.family[c].pop("siblings")
                if "parent" in t.family[c]:
                    t.family[c].pop("parent")
            self.fix_family(t)
            target.family["children"].add(t.index)
            if "children" in target.family[direction]:
                target.family[direction]["children"].add(t.index)
            else:
                target.family[direction]["children"] = {t.index}
            t.family[idir] = {"parent": target.index}
            self.fix_place_children(self.entries[ind])
            self.add_link(target.index, t.index, direction)
            self.update_siblings(target, t, direction)

    def update_siblings(self, par, child, direction):
        pass
        iorient = self.inverse_map[self.orient_map[direction]]
        # avoid adding self to siblings, although in most other cases self is sibling
        if "children" in par.family[direction] and len(par.family[direction]["children"]) > 1:
            if "children" not in child.family[iorient[0]]:
                child.family[iorient[0]].update({"siblings": None})
            if "children" not in child.family[iorient[1]]:
                child.family[iorient[1]].update({"siblings": None})
            for i in par.family[direction]["children"]:
                self.entries[i].family[iorient[0]]["siblings"] =\
                    par.family[direction]["children"].copy()
                self.entries[i].family[iorient[1]]["siblings"] =\
                    par.family[direction]["children"].copy()

    def fix_place_children(self, parent):
        for c in ["u", "d", "l", "r"]:
            if "children" in parent.family[c]:
                self.replace_children(parent, c, c)
                for child in parent.family[c]["children"]:
                    self.fix_place_children(self.entries[child])

    # Currently it replaces children from one direction to opposite
    # But I'd like to replace it from any direction to any other feasible direction
    def replace_children(self, par, f_dir, to_dir):  # , children=None):
        if f_dir == to_dir:
            children = par.family[f_dir].pop("children")
            for c_ind in children:
                pos = self.place_relative(par, f_dir)
                self.entries[c_ind].shape_item.setPos(pos)
                if "children" in par.family[f_dir]:
                    par.family[f_dir]["children"].add(c_ind)
                else:
                    par.family[f_dir]["children"] = {c_ind}
            return
        else:
            direction = to_dir
            idir = f_dir
            iorient = self.inverse_map[self.orient_map[direction]]
            for c_ind in par.family[idir]["children"]:
                self.entries[c_ind].family[idir] = {"parent": par.index}
                if "parent" in self.entries[c_ind].family[idir]:
                    self.entries[c_ind].family[direction] = {}
                if "children" in par.family[direction]:
                    par.family[direction]["children"].add(c_ind)
                else:
                    par.family[direction] = {"children": {c_ind}}
                pos = self.place_relative(par, direction)
                self.entries[c_ind].shape_item.setPos(pos)
                self.entries[c_ind].side = direction
                self.removeItem(self.links[(par.index, c_ind)])
                self.add_link(par.index, c_ind, direction)
                self.check_hide_links(c_ind)
                if "children" not in self.entries[c_ind].family[iorient[0]]:
                    self.entries[c_ind].family[iorient[0]] =\
                        {"siblings": par.family[direction]["children"]}
                if "children" not in self.entries[c_ind].family[iorient[1]]:
                    self.entries[c_ind].family[iorient[1]] =\
                        {"siblings": par.family[direction]["children"]}
                if "children" in self.entries[c_ind].family[idir]:
                    self.replace_children(self.entries[c_ind], idir, direction)
            par.family[idir].pop("children")
            self.fix_family(par)

    def last_child_ordinate(self, t_inds, orientation, axis):
        if orientation == "horizontal":
            coo = lambda item: self.coord(item).x
        else:
            coo = lambda item: self.coord(item).y
        if axis == "pos":
            func = max
            op = operator.add
        else:
            func = min
            op = operator.sub

        axes = [(t_ind, coo(t_ind)) for t_ind in t_inds]
        retval = func(axes, key=lambda x: x[1])
        return op(retval[1], self.entries[retval[0]].
                  shape_item.boundingRect().
                  getRect()[2 if orientation == "horizontal" else 3])

    def drag_and_drop(self, event, pos=None, data=None):
        if not data:
            return
        # pos = event.pos()
        selected = self.selectedItems()
        parent = None
        if selected:
            if len(selected) == 1:
                parent = selected[0]
            if isinstance(parent, Shape):
                parent = parent.text_item
            coords = [QPointF(x[0], x[1]) for x in parent.shape_item.get_link_coords()]
            dirs = ["l", "u", "r", "d"]
            dirz = dict(zip(dirs, coords))
            possible_directions = [d for d in dirs
                                   if parent.family[d][0] not in {"parent", "siblings"}]
            dist_dir = [(self.dist(pos, parent.mapToScene(dirz[p])), p)
                        for p in possible_directions]
            res = min(dist_dir, key=lambda x: x[0])
            # res = min(
            #     [(self.dist(pos, dirz[p]), p) for p in possible_directions],
            #     key=lambda x: x[0])
            self.add_new_child(parent, direction=res[1], data=data)
        else:
            self.add_entry(data, pos)

    def place_relative(self, parent, direction):
        shape_item = parent.shape_item  # shape item for that thought

        def relatives(parent, c_inds):
            return map(lambda x: self.entries[x], parent.family[direction]["children"])

        pos = None
        axis, orientation = self.direction_map[direction]
        displacement = 200
        buffer = 20
        if "parent" in parent.family[direction]:  # [0] == "parent":  # or parent.family[direction][0] == "siblings":
            return
        coords = self.coord(shape_item)
        x, y = coords.x, coords.y
        if "children" in parent.family[direction]:
            children = parent.family[direction]["children"]
            on_side = None
            child_axis = None
            if direction in {"l", "r"}:
                on_side = [1 if self.coord(c).y < y else 0 for c in relatives(parent, children)]
            elif direction in {"u", "d"}:
                on_side = [1 if self.coord(c).x < x else 0 for c in relatives(parent, children)]
            if sum(on_side) < len(on_side)/2:
                child_axis = "neg"
            else:
                child_axis = "pos"

            lco = self.last_child_ordinate(children, "horizontal"
                                           if orientation == "vertical"
                                           else "vertical", child_axis)

            if direction == "l":
                if child_axis == "neg":
                    pos = QPointF(x - displacement, lco - buffer)
                else:
                    pos = QPointF(x - displacement, lco + buffer)
            elif direction == "r":
                if child_axis == "neg":
                    pos = QPointF(x + displacement +
                                  shape_item.boundingRect().getRect()[2], lco - buffer)
                else:
                    pos = QPointF(x + displacement +
                                  shape_item.boundingRect().getRect()[2], lco + buffer)
            elif direction == "u":
                if child_axis == "neg":
                    pos = QPointF(lco - buffer, y - displacement)
                else:
                    pos = QPointF(lco + buffer, y - displacement)
            elif direction == "d":
                if child_axis == "neg":
                    pos = QPointF(lco - buffer, y + displacement + shape_item.boundingRect().getRect()[3])
                else:
                    pos = QPointF(lco + buffer,
                                  y + displacement + shape_item.boundingRect().getRect()[3])
        else:
            if orientation == "horizontal":
                if axis == "neg":  # l
                    pos = QPointF(x - displacement, y)
                else:  # r
                    pos = QPointF(x + displacement + shape_item.boundingRect().getRect()[2], y)
            else:
                if axis == "neg":  # u
                    pos = QPointF(x, y - displacement)
                else:  # d
                    pos = QPointF(x, y + displacement + shape_item.boundingRect().getRect()[3])
        return pos

    def add_new_parent(self, child, paper_data,
                       data={}, shape=Shapes.rectangle, direction=None):
        """Add new parent with data paper_data to child

        Args:
            child: Child entry
            paper_data: Paper data for parent entry
            data: Drawing specific data
            shape: Shape
            direction: Direction


        """
        if isinstance(child, Shape):
            child = child.text_item

        if not direction:
            direction = child.insert_dir
        axis, orientation = self.direction_map[direction]
        pos = self.place_relative(child, direction)
        data.update({'side': direction})
        self.add_entry(paper_data, pos, {"family": {"children": child.index}})

        child.add_relative_in_direction(self.cur_index, direction)
        child.add_parents(self.cur_index)

        c_t = self.entries[self.cur_index]
        idir = self.inverse_map[direction]
        c_t.add_children(child.index)
        c_t.add_relative_in_direction(child.index, idir)
        self.update_siblings(child, c_t, direction)
        self.add_link(child.index, self.cur_index, direction=direction)

    def add_new_child(self, parent, paper_data,
                      data={}, shape=Shapes.rectangle, direction=None):
        if isinstance(parent, Shape):
            parent = parent.text_item

        if not direction:
            direction = parent.insert_dir
        axis, orientation = self.direction_map[direction]
        pos = self.place_relative(parent, direction)
        data.update({'side': direction})
        self.add_entry(paper_data, pos, data={"family": {"parents": parent.index}})

        parent.add_relative_in_direction(self.cur_index, direction)
        parent.add_children(self.cur_index)

        c_t = self.entries[self.cur_index]
        idir = self.inverse_map[direction]
        c_t.add_parents(parent.index)
        c_t.add_relative_in_direction(parent.index, idir)
        self.update_siblings(parent, c_t, direction)
        self.add_link(parent.index, self.cur_index, direction=direction)

    def add_link(self, t1_ind, t2_ind, direction=None):
        if not direction:
            print("cannot insert link without direction")
        self.links[(t1_ind, t2_ind)] = Link(self.entries[t1_ind],
                                            self.entries[t2_ind],
                                            self.entries[t1_ind].color,
                                            scene=self, direction=direction)
        self.addItem(self.links[(t1_ind, t2_ind)])
        self.update()

    def fix_family(self, entry):
        for c in ["l", "u", "r", "d"]:
            keys = list(entry.family[c].keys())
            for k in keys:
                if not entry.family[c][k]:
                    entry.family[c].pop(k)

    def to_pixmap(self, items):
        for item in items:
            p = self.addPixmap(item.to_pixmap())
            p.setPos(item.pos())
            p.setFlag(QGraphicsItem.ItemIsSelectable, False)
            p.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.pix_items.append(p)

    def try_attach_children(self, event, items=None, drag_state="begin"):
        if drag_state == "begin":
            self.drag_begin_pos = event.pos()
            self.dragging_items = items
            for t in self.dragging_items:
                self.thought_positions.append(self.coord(t))
                self.to_pixmap(self.dragging_items)
        elif drag_state == "dragging":
            if self.dragging_items:
                for di in self.dragging_items:
                    di.text_item.set_transluscent(0.6)
                totalRect = reduce(operator.or_,
                                   (i.sceneBoundingRect() for i in self.dragging_items))
                tr = totalRect.getRect()
                buf = 40
                totalRect = QRectF(tr[0] - buf, tr[1] - buf, tr[2] + 2 * buf, tr[3] + 2 * buf)
                self.addRect(totalRect)
                intersection = self.items(totalRect, Qt.IntersectsItemBoundingRect)
                items = list(filter(lambda x: isinstance(x, Shape) and x not in self.dragging_items,
                                    intersection))
                if not items:
                    for arrow in self.arrows:
                        self.removeItem(arrow)
                    self.arrows = []
                    self.target_item = None
                elif items and self.target_item != items[0]:
                    for arrow in self.arrows:
                        self.removeItem(arrow)
                    self.arrows = []
                    self.target_item = None
                    self.target_item = items[0]
                    for di in self.dragging_items:
                        a = Link(di, items[0], QColor(80, 90, 100, 255), collide=True)
                        self.addItem(a)
                        self.arrows.append(a)
                        self.update()
        elif drag_state == "end":
            if not self.target_item:
                for i, tpos in enumerate(self.thought_positions):
                    self.dragging_items[i].setPos(tpos)
                    self.dragging_items[i].text_item.set_opaque()
                self.dragging_items = []
                for p in self.pix_items:
                    self.removeItem(p)
                self.pix_items = []
                for a in self.arrows:
                    self.removeItem(a)
                self.arrows = []
                self.target_item = None
                self.thought_positions = []
            else:
                for p in self.pix_items:
                    self.removeItem(p)
                self.pix_items = []
                for a in self.arrows:
                    self.removeItem(a)
                self.arrows = []
                self.thought_positions = []
                for item in self.dragging_items:
                    item.text_item.set_opaque()
                self.update_parent(self.dragging_items, self.target_item)
                self.target_item = None
                self.update()

    def remove_arrows(self):
        if self.arrows:
            direction = self.arrows[0].direction
            while self.arrows:
                self.removeItem(self.arrows.pop())
            selected = self.get_selected()
            for item in selected:
                if isinstance(item, Shape):
                    item = item.text_item
                item.insert_dir = direction

    def highlight(self, t_inds):
        op_inds = t_inds
        all_inds = set(self.entries.keys())
        tl_inds = all_inds.difference(set(t_inds))
        for t in tl_inds:
            self.entries[t].set_transluscent()
        for t in op_inds:
            self.entries[t].set_opaque()
        if t_inds:
            self.select_one(set(op_inds))

    def un_highlight(self):
        for t in self.entries.values():
            t.set_opaque()

    # Selection
    def select(self, ind):
        self.entries[ind].shape_item.setSelected(True)

    def select_parents(self, entries):
        recurse_ = []
        for e in entries:
            if isinstance(e, Shape):
                e.setSelected(True)
                e = e.text_item
            # elif isinstance(t, Thought):
            #     t.shape_item.setSelected(True)
            if e.family['parents']:
                recurse_ += [self.entries[i] for i in e.family['parents']]
        if recurse_:
            self.select_descendants(recurse_)
        else:
            return

    def select_children(self, entries):
        recurse_ = []
        for e in entries:
            if isinstance(e, Shape):
                e.setSelected(True)
                e = e.text_item
            # elif isinstance(t, Thought):
            #     t.shape_item.setSelected(True)
            if e.family['children']:
                recurse_ += [self.entries[i] for i in e.family['children']]
        if recurse_:
            self.select_children(recurse_)
        else:
            return

    def select_all(self):
        selected = self.selectedItems()
        if not selected:
            for ts in self.entries.values():
                ts.shape_item.setSelected(True)
        else:
            if len(selected) == 1:
                thought = selected[0].text_item
                for c in ['u', 'd', 'l', 'r']:
                    if 'siblings' in thought.family[c]:
                        for s in thought.family[c]['siblings']:
                            self.select(s)

    # links also?
    def unselect_all(self):
        self.clearSelection()

    def select_new_thought(self):
        self.select_one(self.cur_index)
        self.entries[self.cur_index].set_editable()

    def exit_app(self):
        # check if saving
        # if not:
        pass
