try:
    import unittest.mock as mock
except ImportError:
    import mock
import string

import pytest

from jumpssh import util


mock_input = '__builtin__.raw_input' if util.PY2 else 'builtins.input'


def test_id_generator():
    # basic checks on size
    assert int(util.id_generator(size=1, chars=string.digits)) < 10
    assert len(util.id_generator(size=5)) == 5
    # basic checks on character types
    assert util.id_generator(size=5).isalnum()
    assert util.id_generator(size=8, chars=string.ascii_letters).isalpha()
    assert util.id_generator(size=8, chars=string.digits).isdigit()


def test_yes_no_query_invalid_input_parameters():
    with pytest.raises(ValueError):
        util.yes_no_query('A question ?', default='invalid param value')
    with pytest.raises(ValueError):
        util.yes_no_query('A question ?', interrupt='invalid param value')


@pytest.mark.parametrize("answer", ['y', 'Y', 'yes', 'YES', 'Yes'])
def test_yes_no_query_nominal_case_yes(answer, monkeypatch):
    monkeypatch.setattr(mock_input, lambda x: answer)
    assert util.yes_no_query('A question ?') is True


@pytest.mark.parametrize("answer", ['n', 'N', 'no', 'NO', 'No'])
def test_yes_no_query_nominal_case_no(answer, monkeypatch):
    monkeypatch.setattr(mock_input, lambda x: answer)
    assert util.yes_no_query('A question ?') is False


@pytest.mark.parametrize("answer", [' ', '  ', '\t'])
def test_yes_no_query_empty_anwser(answer, monkeypatch):
    monkeypatch.setattr(mock_input, lambda x: answer)
    assert util.yes_no_query('A question ?', default=True) is True
    assert util.yes_no_query('A question ?', default=False) is False


def test_yes_no_query_interrupt():
    with mock.patch(mock_input, side_effect=KeyboardInterrupt('Fake Ctrl-C')):
        assert util.yes_no_query('A question ?', interrupt=True) is True
        assert util.yes_no_query('A question ?', interrupt=False) is False


def test_yes_no_query_eof():
    with mock.patch(mock_input, side_effect=EOFError('Fake EOFError')):
        assert util.yes_no_query('A question ?', default=True) is True
        assert util.yes_no_query('A question ?', default=False) is False
        with pytest.raises(EOFError):
            util.yes_no_query('A question ?')
