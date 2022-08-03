from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest

from common_funcs import run_shell_cmd, get_file_size, get_img_wxh, \
    get_name_decor, split_fstring_not_args


def test_run_shell_cmd():
    result_text = run_shell_cmd(['stat', '-c' '%s %n', "white_100x100.png"])
    assert result_text.strip() == '694 white_100x100.png'


def test_get_file_size():
    result_text = get_file_size("white_100x100.png")
    assert result_text == "694"


def test_get_img_wxh():
    wxh = get_img_wxh("white_100x100.png")
    assert wxh == [100, 100]


def test_get_name_decor():
    decor = get_name_decor(640, 480, "xzmp")
    assert decor == "-640x480.xzmp"


def test_split_fstring_not_args():
    in_fstr = "split into words {except_where} we are substituting {var1} " \
              "fstrings. {snippet1}."
    f_str_vars = {
        "except_where": "except where",
        "var1": "for",
        "snippet1": "Here's another preserved bit"
    }
    results = split_fstring_not_args(f_str_vars, in_fstr)
    assert results == [
        "split", "into", "words", "except where", "we", "are", "substituting",
        "for", "fstrings.", "Here's another preserved bit."]



