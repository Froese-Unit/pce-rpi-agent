from random import randint

from pce import settings as st


def wrap_around(x):
    return x % st.ENV_WIDTH


def overlaps(a, b):
    return any(
        (
            # neither a nor b are wrapped
            not iswrapped(a)
            and not iswrapped(b)
            and any(
                [
                    a.xleft <= b.xleft <= a.xright,
                    a.xleft <= b.xright <= a.xright,
                    b.xleft <= a.xleft <= b.xright,
                    b.xleft <= a.xright <= b.xright,
                ]
            ),
            # a is wrapped, b is not
            iswrapped(a)
            and not iswrapped(b)
            and any([a.xleft <= b.xright, b.xleft <= a.xright]),
            # a is not wrapped, b is
            not iswrapped(a)
            and iswrapped(b)
            and any([b.xleft <= a.xright, a.xleft <= b.xright]),
            # a and b are both wrapped
            iswrapped(a) and iswrapped(b),
        )
    )


def iswrapped(obj):
    return obj.xleft > obj.xright


class Object:
    def __init__(self, x, width):
        self.width = width
        self.x = x

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, new_x):
        self._x = wrap_around(new_x)

    @property
    def xleft(self):
        return wrap_around(self.x - self.width / 2)

    @xleft.setter
    def xleft(self, _):
        raise ValueError("Use x to set a new position")

    @property
    def xright(self):
        return wrap_around(self.x + self.width / 2)

    @xright.setter
    def xright(self, _):
        raise ValueError("Use x to set a new position")


class Shadow:
    def __init__(self, reference, side):
        self.reference = reference
        self.delta = side * randint(*st.SHADOW_DELTA_RANGE)

    @property
    def width(self):
        return self.reference.width

    @property
    def xleft(self):
        return wrap_around(self.reference.xleft + self.delta)

    @property
    def x(self):
        return wrap_around(self.reference.x + self.delta)

    @property
    def xright(self):
        return wrap_around(self.reference.xright + self.delta)
