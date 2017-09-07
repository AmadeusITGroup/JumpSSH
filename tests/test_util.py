import string

from jumpssh import util


def test_id_generator():
    # basic checks on size
    assert int(util.id_generator(size=1, chars=string.digits)) < 10
    assert len(util.id_generator(size=5)) == 5
    # basic checks on character types
    assert util.id_generator(size=5).isalnum()
    assert util.id_generator(size=8, chars=string.ascii_letters).isalpha()
    assert util.id_generator(size=8, chars=string.digits).isdigit()
