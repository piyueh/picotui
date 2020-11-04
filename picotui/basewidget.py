import os

from .screen import Screen
from .defs import KEYMAP as _KEYMAP


# Standard widget result actions (as return from .loop())
ACTION_OK = 1000
ACTION_CANCEL = 1001
ACTION_NEXT = 1002
ACTION_PREV = 1003

class Widget(Screen):
    """The base class for all widgets.

    Attributes
    ----------
    kbuf : bytes
        Used as a buffer space to store input bytes.
    signals : list of functions
        This variable stores the callback functions for different signals. Callback functions can
        be registered with the `on` method.
    x, y : int
        Coordinates of this widget. They are set through the `set_xy` method.
    w, h : int
        The width and the height of this widget. These attributes are initialized in derived classes.

    Note
    ----
    Some member functions/attributes are not defined in this class, but are assumed to be defined in
    derived classes in some situations:

        1. `handle_mouse`
        2. `handle_key`
        3. `w`
        4. `h`
    """

    def __init__(self):
        # constructor's docstring is should be handled by the class' docstring
        self.kbuf = b""
        self.signals = {}

    def set_xy(self, x, y):
        """Sets the x and y coordinates of this widget.

        Parameters
        ----------
        x : int
            The column of where the left boundary of this widget is at.
        y : int
            The line of where the top boundary of this widget is at.
        """
        self.x = x
        self.y = y

    def inside(self, x, y):
        """Checks if a coordinate set (x, y) is inside this widget.

        Parameters
        ----------
        x, y : int
            The x and y coordinates that will be checked.

        Note
        ----
        This function assumes the current widget has attributes `w` and `h`.
        """
        return self.y <= y < self.y + self.h and self.x <= x < self.x + self.w

    def signal(self, sig):
        """Calls the callback function of a given signal.

        Parameters
        ----------
        sig : hashable object
            The signal.

        Raises
        ------
        KeyError
            If the callback of the given signal has not been set through the `on` method.
        """
        if sig in self.signals:
            self.signals[sig](self)

    def on(self, sig, handler):
        """Registers the callback function of a signal.

        Parameters
        ----------
        sig : hashable object
            The signal.
        handler : callable object
            The callback function that takes in no arguments.
        """
        self.signals[sig] = handler

    @staticmethod
    def longest(items):
        """Returns the longest length of the objects in a list-like.

        Parameters
        ----------
        items : list-like
            A list of objects that have `__len__` member function.
        """
        if not items:
            return 0
        return max((len(t) for t in items))

    def set_cursor(self):
        """Disables the cursor."""
        # By default, a widget doesn't use text cursor, so disables it
        self.cursor(False)

    def get_input(self):
        """Obtains the input from the standard input.

        Returns
        -------
        1. a list of two integers, i.e., [col, row]
            If the input is a report from mouse tracking (with X10 compatibility mode), then
            returns the coordinates [col, row] of where the mouse click happened.
        2. a str
            If the input key is found in `KEYMAP`, then returns the string representation of the key.
        3. a byte
            If the input key is not found in `KEYMAP`, then returns the original byte representation
            of the key.
        """
        if self.kbuf:
            key = self.kbuf[0:1]
            self.kbuf = self.kbuf[1:]
        else:
            key = os.read(0, 32)
            if key[0] != 0x1b:
                key = key.decode()
                self.kbuf = key[1:].encode()
                key = key[0:1].encode()
        key = _KEYMAP.get(key, key)

        if isinstance(key, bytes) and key.startswith(b"\x1b[M") and len(key) == 6:
            row = key[5] - 33
            col = key[4] - 33
            return [col, row]

        return key

    def handle_input(self, inp):
        """Calls the callback function corresponding to key or mouse inputs.

        Parameters
        ----------
        inp : a list, str, or byte
            Usually the return from `get_input`, though it actually depends on how derived classes
            define the members `handle_mouse` and `handle_key`.

        Returns
        -------
        res
            The return depends on how derived classes define `handle_mouse` and `handle_key`.
        """
        if isinstance(inp, list):
            res = self.handle_mouse(inp[0], inp[1])
        else:
            res = self.handle_key(inp)
        return res

    def loop(self):
        """A loop to obtain inputs and reacts until obtaining desired signal.

        Depending on how derived classes define `handle_mouse` and `handle_key`, if the returns
        of these callbacks are not None and not True, the loop stops and return the returns of these
        callbacks.
        """
        self.redraw()
        while True:
            key = self.get_input()
            res = self.handle_input(key)

            if res is not None and res is not True:
                return res


class FocusableWidget(Widget):
    # If set to non-False, pressing Enter on this widget finishes
    # dialog, with Dialog.loop() return value being this value.
    finish_dialog = False


class EditableWidget(FocusableWidget):

    def get(self):
        raise NotImplementedError


class ChoiceWidget(EditableWidget):

    def __init__(self, choice):
        super().__init__()
        self.choice = choice

    def get(self):
        return self.choice


# Widget with few internal selectable items
class ItemSelWidget(ChoiceWidget):

    def __init__(self, items):
        super().__init__(0)
        self.items = items

    def move_sel(self, direction):
        self.choice = (self.choice + direction) % len(self.items)
        self.redraw()
        self.signal("changed")
