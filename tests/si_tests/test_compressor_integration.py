import time
from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest

from compressor import get_widths_and_heights, ResolutionsList, \
    run_shell_cmd, get_file_size, get_img_wxh, resize, process_args
from wp_api.api_app import WP_API


def setup_module(module):
    wp_api = WP_API()
    wp_api.delete_all_my("media")


def test_resize():
    subject_name = "testing-how-it-looked-installed"
    # 300x118, 768x302, 1024x402, and 150x150
    with patch("builtins.input", return_value='0') as mocked_input:
        resize("{}.png".format(subject_name))
    wp_api = WP_API()
    # We don't *need* to give the .webp extension, but it will be smallest.
    generated_media = wp_api.fetch_all(
        "media?search={}.webp".format(subject_name), {})
    suffices = sorted([(v["width"], v["height"]) for v in
                       generated_media[0]["media_details"]["sizes"].values()])
    assert suffices == sorted([
        (150,150), (300,118), (768,302), (1024,402), (1080,424)
    ])


def teardown_module(module):
    """teardown any state after all tests herein have run."""
    wp_api = WP_API()
    number_needing_deletion, number_after_deletion =\
        wp_api.delete_all_my("media")
    assert number_needing_deletion >= number_after_deletion
    assert number_after_deletion == 0


