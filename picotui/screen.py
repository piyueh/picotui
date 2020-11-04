import os
import signal


class Screen:
    """Base class for controlling a terminal screen.

    This class serves as

        1. a base class for widgets and
        2. a namespace of static methods that interacts with the current terminal's screen.

    Attributes
    ----------
    org_termios : list
        The terminal attributes at the time when the `init_tty` is called.
    screen_redraw : callable object
        The function that redraws things on the screen. It is set through `set_screen_redraw`.

    References
    ----------
    [1] XTerm Control Sequences, URL: https://invisible-island.net/xterm/ctlseqs/ctlseqs.pdf
    """

    @staticmethod
    def wr(s):
        """Writes bytes or a string to the current terminal screen.

        Parameters
        ----------
            s : str
                The byte/string to be output.
        """
        # TODO: When Python is 3.5, update this to use only bytes
        if isinstance(s, str):
            s = bytes(s, "utf-8")
        os.write(1, s)

    @staticmethod
    def wr_fixedw(s, width):
        """Writes a string with a fixed width to the current terminal screen.

        Parameters
        ----------
            s : str
                The string to be output.
            width : int
                The width.
        """
        # TODO: can be simply handled with Python 3's string formatting capability.
        s = s[:width]
        Screen.wr(s)
        Screen.wr(" " * (width - len(s)))
        # Doesn't work here, as it doesn't advance cursor
        #Screen.clear_num_pos(width - len(s))

    @staticmethod
    def cls():
        """Clears the entire screen."""
        Screen.wr(b"\x1b[2J")

    @staticmethod
    def goto(x, y):
        """Moves the cursor to a specific line and a specific column.

        Parameters
        ----------
            x : int
                The column where the cursor will be.
            y : int
                The line where the cursor will be.
        """
        # TODO: When Python is 3.5, update this to use bytes
        Screen.wr("\x1b[%d;%dH" % (y + 1, x + 1))

    @staticmethod
    def clear_to_eol():
        """Clears from the current cursor position to the end of line."""
        Screen.wr(b"\x1b[0K")

    # Clear specified number of positions
    @staticmethod
    def clear_num_pos(num):
        """Clears characters on the right of the cursor.

        Parameters
        ----------
        num : int
            Number of characters to be cleared on the right of the cursor.
        """
        if num > 0:
            Screen.wr("\x1b[%dX" % num)

    @staticmethod
    def attr_color(fg, bg=-1):
        """Changes the foreground and background colors of the future outputs on the screen.

        This is done by writing the control squence of the colors to standard output.

        Note
        ----
        1. If `bg` is -1, the background color will be determined by `fg`: `bg` will be the quotient
           of `bg / 16`. In this case, the allowed range of `fg` is 0 to 143. And `fg` will be
           internally converted to 0 to 15. 0 to 7 are the specified foreground color with regular
           font, while 8 to 15 are the color with bold face font.

        2. If `bg` is None, the background color will be black. And if `fg` is greater than 15, the
           foreground color will just be white and with bold face font.

        3. If `bg` is not None, then the allowed value range is 0 to 8.

        Parameters
        ----------
            fg : int
                The ANSI color code for foreground.
            bg : int
                The ANSI color code for background. Default: -1.
        """
        if bg == -1:
            bg = fg >> 4
            fg &= 0xf
        # TODO: Switch to b"%d" % foo when py3.5 is everywhere
        if bg is None:
            if (fg > 8):
                Screen.wr("\x1b[%d;1m" % (fg + 30 - 8))
            else:
                Screen.wr("\x1b[%dm" % (fg + 30))
        else:
            assert bg <= 8
            if (fg > 8):
                Screen.wr("\x1b[%d;%d;1m" % (fg + 30 - 8, bg + 40))
            else:
                Screen.wr("\x1b[0;%d;%dm" % (fg + 30, bg + 40))

    @staticmethod
    def attr_reset():
        """Resets the foreground and background colors of the future outputs on the screen."""
        Screen.wr(b"\x1b[0m")

    @staticmethod
    def cursor(onoff):
        """Shows or turns off the cursor on the screen.

        Parameters
        ----------
        onoff : boolean
            Whether to show the cursor or not.
        """
        if onoff:
            Screen.wr(b"\x1b[?25h")
        else:
            Screen.wr(b"\x1b[?25l")

    def draw_box(self, left, top, width, height):
        """Draws the border lines of a box on the screen.

        Parameters
        ----------
        left : integer
            The location (column) of where the left border is at.
        top : integer
            The location (line) of where the top border is at.
        width : integer
            The total columns the box spans.
        height : integer
            The total lines the box spans.
        """
        # Use http://www.utf8-chartable.de/unicode-utf8-table.pl
        # for utf-8 pseudographic reference
        bottom = top + height - 1
        self.goto(left, top)
        # "┌"
        self.wr(b"\xe2\x94\x8c")
        # "─"
        hor = b"\xe2\x94\x80" * (width - 2)
        self.wr(hor)
        # "┐"
        self.wr(b"\xe2\x94\x90")

        self.goto(left, bottom)
        # "└"
        self.wr(b"\xe2\x94\x94")
        self.wr(hor)
        # "┘"
        self.wr(b"\xe2\x94\x98")

        top += 1
        while top < bottom:
            # "│"
            self.goto(left, top)
            self.wr(b"\xe2\x94\x82")
            self.goto(left + width - 1, top)
            self.wr(b"\xe2\x94\x82")
            top += 1

    def clear_box(self, left, top, width, height):
        """Clears the border lines of a box defined at a given location and size.

        Parameters
        ----------
        left : integer
            The location (column) of where the left border is at.
        top : integer
            The location (line) of where the top border is at.
        width : integer
            The total columns the box spans.
        height : integer
            The total lines the box spans.
        """
        # doesn't work
        #self.wr("\x1b[%s;%s;%s;%s$z" % (top + 1, left + 1, top + height, left + width))
        s = b" " * width
        bottom = top + height
        while top < bottom:
            self.goto(left, top)
            self.wr(s)
            top += 1

    def dialog_box(self, left, top, width, height, title=""):
        """A dialog box that can have a title.

        The title will be shown at the top-left corner and overwrite part of the top border line.

        Parameters
        ----------
        left : integer
            The location (column) of where the left border is at.
        top : integer
            The location (line) of where the top border is at.
        width : integer
            The total columns the box spans.
        height : integer
            The total lines the box spans.
        title : str
            The title. Default: "".
        """
        self.clear_box(left + 1, top + 1, width - 2, height - 2)
        self.draw_box(left, top, width, height)
        if title:
            #pos = (width - len(title)) / 2
            pos = 1
            self.goto(left + pos, top)
            self.wr(title)

    @classmethod
    def init_tty(cls):
        """Gets the attributes of the current terminal and set the terminal to raw mode."""
        import tty, termios
        cls.org_termios = termios.tcgetattr(0)
        tty.setraw(0)

    @classmethod
    def deinit_tty(cls):
        """Recovers the terminal attributes back to what they were the last time init_tty was called."""
        import termios
        termios.tcsetattr(0, termios.TCSANOW, cls.org_termios)

    @classmethod
    def enable_mouse(cls):
        """Enables mouse tracking.

        Enables X10 compatibility mode only. This mode sends an escape sequence only on button
        press, encoding the location and the mouse button pressed.
        """
        # Mouse reporting - X10 compatibility mode
        cls.wr(b"\x1b[?9h")

    @classmethod
    def disable_mouse(cls):
        """Disables mouse tracking."""
        # Mouse reporting - X10 compatibility mode
        cls.wr(b"\x1b[?9l")

    @classmethod
    def screen_size(cls):
        """Returns the width and height of the current terminal's screen.

        Returns
        -------
        width : int
            The number of columns of the current screen.
        height : int
            The number of lines of the current screen.
        """
        import select
        cls.wr(b"\x1b[18t")
        res = select.select([0], [], [], 0.2)[0]
        if not res:
            return (80, 24)
        resp = os.read(0, 32)
        assert resp.startswith(b"\x1b[8;") and resp[-1:] == b"t"
        vals = resp[:-1].split(b";")
        return (int(vals[2]), int(vals[1]))

    # Set function to redraw an entire (client) screen
    # This is called to restore original screen, as we don't save it.
    @classmethod
    def set_screen_redraw(cls, handler):
        """Sets up the function for redrawing."""
        cls.screen_redraw = handler

    @classmethod
    def set_screen_resize(cls, handler):
        """Sets the function to call when receiving a SIGWINCH signal.

        Note
        ----
        The signal SIGWINCH is sent to a terminal application when the size of the terminal window
        changes.
        """
        signal.signal(signal.SIGWINCH, lambda sig, stk: handler(cls))
