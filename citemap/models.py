from dataclasses import dataclass


@dataclass
class xy:
    x: int
    y: int

    def __init__(self, *args):
        if len(args) == 2:
            self.x, self.y = args
        elif isinstance(args[0], tuple):
            self.x, self.y = args[0]
        else:
            maybe_x = getattr(args[0], "x")
            if maybe_x:
                if callable(maybe_x):
                    self.x, self.y = args[0].x(), args[0].y()
                else:
                    self.x, self.y = args[0].x, args[0].y


@dataclass
class rect:
    x: float
    y: float
    width: float
    height: float

    def __init__(self, *args):
        if len(args) == 2:
            self.x = args[0]
            self.y = args[1]
            self.width = args[2]
            self.height = args[3]
        else:
            self.x = args[0][0]
            self.y = args[0][1]
            self.width = args[0][2]
            self.height = args[0][3]


