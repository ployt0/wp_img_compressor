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
    ("100x100", []),
    ("150x150", ["150x150"]),
    ("200x300", ["150x150"]),
    ("200x1024", ["59x300", "150x150"]),
    ("300x200", ["150x150"]),
    ("300x400", ["150x150", "225x300"]),
    ("400x300", ["150x150", "300x225"]),
    ("768x100", ["150x100", "300x39"]),
    ("1024x200", ["150x150", "300x59", "768x150"]),
])
def test_image_resizing(source_size, expected_dims):
    """
    :param source_size: determines what the resizings should be.
    :param expected_dims: these don't include the source size since the source
        is never affected by the resizing operations.
    """
    wp_api = WP_API()
    this_dir = Path(__file__).parent.resolve()
    src_file = os.path.join(this_dir, "white_{}.png".format(source_size))
    response = wp_api.upload_media(src_file, src_file)
    assert response.ok
    if expected_dims:
        # Only if we generate a thumbnail are any resize results returned.
        expected_dims.append(source_size)
    suffices = sorted(["{}x{}".format(v["width"], v["height"])
                for v in response.json()["media_details"]["sizes"].values()])
    assert suffices == sorted(expected_dims)


def teardown_module(module):
    wp_api = WP_API()
    wp_api.delete_all_my("media")
