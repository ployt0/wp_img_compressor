"""
Rather than regression testing, it may be easier to just have our compression
script find the resizing directly from the server, then it can make comparisons
with WordPress's best efforts more easily.

The examples presented here are invalidated if the default width and height
of the medium and large images sizes change.
"""
import json
import os
from pathlib import Path

import pytest
# PyCharm flags this, but I've told it PYTHONPATH=.. and it works.
from wp_api.api_app import WP_API


@pytest.mark.parametrize("source_size,expected_dims", [
    ((100,100), []),
    ((150,150), [(150,150),]),
    ((200,300), [(150,150),]),
    ((200,1024), [(59,300), (150,150),]),
    ((300,200), [(150,150),]),
    ((300,400), [(150,150), (225,300),]),
    ((400,300), [(150,150), (300,225),]),
    ((768,100), [(150,100), (300,39),]),
    ((1024,200), [(150,150), (300,59), (768,150),]),
    ((2560,1440), [(150,150), (300,169), (768,432), (1024,576), (1536,864), (2048,1152),]),
    ((4000,3000), [(150,150), (300,225), (768,576), (1024,768), (1536,1152), (2048,1536),]),
])
def test_image_resizing(source_size, expected_dims):
    """
    :param source_size: determines what the resizings should be.
    :param expected_dims: these don't include the source size since the source
        is never affected by the resizing operations.
    """
    wp_api = WP_API()
    this_dir = Path(__file__).parent.resolve()
    src_file = os.path.join(this_dir, "white_{}x{}.png".format(*source_size))
    response = wp_api.upload_media(src_file, src_file)
    assert response.ok
    if expected_dims:
        # Only if we generate a thumbnail are any resize results returned.
        expected_dims.append(source_size)
    suffices = sorted([(v["width"], v["height"])
                for v in response.json()["media_details"]["sizes"].values()])
    assert suffices == sorted(expected_dims)


def teardown_module(module):
    wp_api = WP_API()
    wp_api.delete_all_my("media")
