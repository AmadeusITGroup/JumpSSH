"""
Useful functions used by the rest of jumpssh.
"""
from __future__ import print_function
import random
import string
import sys

PY2 = sys.version_info[0] < 3


def id_generator(size=6, chars=string.ascii_letters + string.digits):
    """Generate random string with specified size and set of characters

    :param size: length of the expected string
    :param chars: expected characters in the string
    :return: random string
    """
    return ''.join(random.choice(chars) for _ in range(size))


def yes_no_query(question, default=None, interrupt=None):
    """Ask a yes/no question via standard input and return a boolean answer.

    If default is given, it is used if the user input is empty.
    If interrupt is given, it is used if the user presses Ctrl-C.
    An EOF is treated as the default answer.  If there is no default, an exception is raised to prevent infinite loops.
    Valid answers are: y/yes/n/no (match is not case sensitive).
    If invalid input is given, the user will be asked until they actually give valid input.

    :param question: A question that is presented to the user.
    :param default: The default value when enter is pressed with no value.
        When None, there is no default value and the query will loop.
    :param interrupt: The default value when the user presses Ctrl-C
    :return: A bool indicating whether user has entered yes or no.
    :rtype: bool
    """
    valid_answers = {'y': True, 'n': False, 'yes': True, 'no': False}
    default_dict = {  # default => prompt default string
        None: "[y/n]",
        True: "[Y/n]",
        False: "[y/N]",
    }

    # validate input parameters
    if default not in default_dict:
        raise ValueError("Invalid value for parameter 'default': '%s'. Possible values: [%s]"
                         % (default, ','.join(map(str, default_dict.keys()))))
    if interrupt not in default_dict:
        raise ValueError("Invalid value for parameter 'interrupt': '%s'. Possible values: [%s]"
                         % (interrupt, ','.join(map(str, default_dict.keys()))))

    prompt_str = "%s %s " % (question, default_dict[default])

    # check user input
    answer = None
    while answer not in valid_answers:
        try:
            answer = (raw_input(prompt_str) if PY2 else input(prompt_str)).strip().lower()  # noqa
            # response was an empty string and default value is set
            if not answer and isinstance(default, bool):
                return default
        except KeyboardInterrupt:
            if isinstance(interrupt, bool):
                print()
                return interrupt
        except EOFError:
            if isinstance(default, bool):
                print()
                return default
            else:
                raise

    return valid_answers[answer]
