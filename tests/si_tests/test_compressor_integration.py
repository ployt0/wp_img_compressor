from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest

from compressor import get_widths_and_heights, ResolutionsList, \
    run_shell_cmd, get_file_size, get_img_wxh, resize, process_args
from wp_api.api_app import WP_API



def test_resize():
    # 300x118, 768x302, 1024x402, and 150x150
    with patch("builtins.input", lambda _: '1') as mocked_open:
        resize("testing-how-it-looked-installed.png")


def teardown_module(module):
    """teardown any state after all tests herein have run."""
    wp_api = WP_API()
    number_needing_deletion, number_after_deletion =\
        wp_api.delete_all_my("media")
    assert number_needing_deletion >= number_after_deletion
    assert number_after_deletion == 0


