"""
Useful functions used by the rest of jumpssh.
"""
import random
import string


def id_generator(size=6, chars=string.ascii_letters + string.digits):
    """Generate random string with specified size and set of characters

    :param size: length of the expected string
    :param chars: expected characters in the string
    :return: random string
    """
    return ''.join(random.choice(chars) for _ in range(size))
