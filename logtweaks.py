import sys
import logging
import collections


class PrettyStreamHandler(logging.StreamHandler):
    """Wrap log messages with severity-dependent ANSI terminal colours.

    Use in place of :class:`logging.StreamHandler` to have log messages coloured
    according to severity.

    >>> handler = PrettyStreamHandler()
    >>> handler.setFormatter(logging.Formatter('[%(levelname)-8s] %(message)s'))
    >>> logging.getLogger('').addHandler(handler)

    *stream* corresponds to the same argument to :class:`logging.StreamHandler`,
    defaulting to stderr.

    *colour* overrides TTY detection to force colour on or off.

    This source for this class is released into the public domain.

    .. codeauthor:: Alan Briolat <alan.briolat@gmail.com>
    """
    #: Mapping from logging levels to ANSI colours.
    COLOURS = {
        logging.DEBUG: '\033[36m',      # Cyan foreground
        logging.WARNING: '\033[33m',    # Yellow foreground
        logging.ERROR: '\033[31m',      # Red foreground
        logging.CRITICAL: '\033[31;7m'  # Red foreground, inverted
    }
    #: ANSI code for resetting the terminal to default colour.
    COLOUR_END = '\033[0m'

    def __init__(self, stream=None, colour=None):
        super(PrettyStreamHandler, self).__init__(stream)
        if colour is None:
            self.colour = self.stream.isatty()
        else:
            self.colour = colour

    def format(self, record):
        """Get a coloured, formatted message for a log record.

        Calls :func:`logging.StreamHandler.format` and applies a colour to the
        message if appropriate.
        """
        msg = super(PrettyStreamHandler, self).format(record)
        if self.colour:
            colour = self.COLOURS.get(record.levelno, '')
            return colour + msg + self.COLOUR_END
        else:
            return msg


def indent(data, amount=1, string='  '):
    return ''.join(string * amount + line for line in data.splitlines(True))


class IndentingLoggerAdapter(logging.LoggerAdapter):
    """Stateful logger adapter that indents messages.

    Provides :meth:`indent` and :meth:`outdent` to increase and decrease the
    indent level.  All messages have the indentation prepended to them when
    they pass through the adapter.

    >>> log = IndentingLoggerAdapter(logging.getLogger('foo'))
    >>> log.debug('hello world')
    >>> log.indent()
    >>> log.debug('I am indented')
    >>> log.outdent()
    >>> log.debug('and now I am not')

    """
    def __init__(self, log):
        super(IndentingLoggerAdapter, self).__init__(log, None)
        self._indent_level = 0

    def indent(self):
        self._indent_level += 1

    def outdent(self):
        self._indent_level = max(0, self._indent_level - 1)

    def process(self, msg, kwargs):
        return (indent(msg, self._indent_level), kwargs)


def apply_mapping_arg_fix():
    """
    Allow first log record argument to be any mapping, not just dict.

    This is a monkey-patch to work around http://bugs.python.org/issue21172,
    which is fixed in 2.7.7 and 3.4.1.  Currently this only works for 2.7.x
    because the argument order to :meth:`LogRecord.__init__` are specific to
    that version.
    """
    assert (2, 7, 0) <= sys.version < (2, 7, 0), \
            'Fix only works for Python 2.7 (fixed in 2.7.7)'
    assert logging.LogRecord.__init__ is not _new_LogRecord_init, \
            'Fix already applied'
    logging.LogRecord.__init__ = _new_LogRecord_init

_old_LogRecord_init = logging.LogRecord.__init__
# This argument list is only correct for Python 2.7
def _new_LogRecord_init(self, name, level, pathname, lineno,
                       msg, args, exc_info, func=None):
    # Initialise LogRecord as normal
    _old_LogRecord_init(self, name, level, pathname, lineno,
                        msg, args, exc_info, func)
    # Perform same check as the original constructor, but replace
    # isinstance(args[0], dict) check with isinstance(args[0], Mapping), to
    # match the expectations of the % operator
    if args and len(args) == 1 and isinstance(args[0], collections.Mapping) and args[0]:
        # Don't re-do the special case if it succeeded the first time
        if self.args is not args[0]:
            self.args = args[0]
