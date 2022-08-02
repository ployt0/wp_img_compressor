from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest

from compressor import get_widths_and_heights, ResolutionsList, run_shell_cmd,\
    get_file_size, get_img_wxh, resize, process_args, get_name_decor, process_outputs


def test_parse_args_for_monitoring_help():
    with pytest.raises(SystemExit):
        process_args(["-h"])


@patch("compressor.resize", autospec=True)
def test_parse_args(mock_resize):
    MOCK_ARGS_LIST = ["sentinel.imgfile"]
    process_args(MOCK_ARGS_LIST)
    mock_resize.assert_called_once_with(
        MOCK_ARGS_LIST[0],
        "config.json",
        False,
        False,
        False,
        False
    )


@patch("compressor.resize", autospec=True)
def test_parse_args_noresize(mock_resize):
    MOCK_ARGS_LIST = ["sentinel.imgfile", "-f"]
    process_args(MOCK_ARGS_LIST)
    mock_resize.assert_called_once_with(
        MOCK_ARGS_LIST[0],
        "config.json",
        False,
        False,
        False,
        True
    )


@patch("compressor.resize", autospec=True)
def test_parse_args_config(mock_resize):
    MOCK_ARGS_LIST = ["sentinel.imgfile", "-c", "top_secret_conf.json"]
    process_args(MOCK_ARGS_LIST)
    mock_resize.assert_called_once_with(
        MOCK_ARGS_LIST[0],
        "top_secret_conf.json",
        False,
        False,
        False,
        False
    )


@patch("compressor.ImgConvertor", autospec=True)
@patch("compressor.os.path.isfile", autospec=True, return_value=True)
@patch("compressor.process_outputs", autospec=True)
@patch("compressor.get_img_wxh", return_value=[640, 480])
@patch("compressor.get_widths_and_heights", return_value=(sentinel.widths_and_heights, sentinel.thumbnail))
def test_resize(mock_get_all_whs, mock_get_1wh, mock_process_outputs,
                mock_isfile, mock_img_conv):
    img_name = "this is a file path and name.jpg"
    resize(img_name, "config.json", False, False, False)
    mock_process_outputs.assert_called_once_with(
        640, 480, mock_img_conv.return_value, sentinel.widths_and_heights, "config.json"
    )
    mock_get_1wh.assert_called_once_with(img_name)
    mock_get_all_whs.assert_called_once_with(640, 480)
    mock_isfile.assert_called_once_with(img_name)
    mock_img_conv.assert_called_once_with(img_name, sentinel.widths_and_heights, "tmp/")


@patch("compressor.ImgConvertor", autospec=True)
@patch("compressor.os.path.isfile", autospec=True, return_value=True)
@patch("compressor.process_outputs", autospec=True)
@patch("compressor.get_img_wxh", return_value=[640, 480])
@patch("compressor.get_widths_and_heights", return_value=(sentinel.widths_and_heights, sentinel.thumbnail))
def test_resize_fullsize_only(
        mock_get_all_whs, mock_get_1wh, mock_process_outputs, mock_isfile,
        mock_img_conv):
    img_name = "this is a file path and name.jpg"
    resize(img_name, "config.json", False, False, False, True)
    mock_process_outputs.assert_called_once_with(
        640, 480, mock_img_conv.return_value, sentinel.widths_and_heights, "config.json"
    )
    mock_get_1wh.assert_called_once_with(img_name)
    mock_get_all_whs.assert_called_once_with(640, 480)
    mock_isfile.assert_called_once_with(img_name)
    mock_img_conv.assert_called_once_with(img_name, sentinel.widths_and_heights, "tmp/")


@patch("compressor.os.path.isfile", autospec=True, return_value=False)
@patch("compressor.Path", autospec=True)
def test_resize_missing_file(mock_path, mock_isfile):
    img_name = "this is a file path and name.jpg"
    with pytest.raises(FileNotFoundError) as fnfe:
        resize(img_name)
    mock_path.assert_called_once_with(img_name)
    mock_isfile.assert_called_once_with(img_name)


@patch("compressor.os.path.isfile", autospec=True, return_value=True)
def test_resize_unknown_file_ext(mock_isfile):
    img_name = "this is a file path and name.wookie"
    with pytest.raises(RuntimeError) as fnfe:
        resize(img_name)
    mock_isfile.assert_called_once_with(img_name)


def test_parse_args_for_help():
    with pytest.raises(SystemExit):
        process_args(["-h"])


def combined_widths_and_heights(w, h):
    widths_and_heights, thmb = get_widths_and_heights(w, h)
    if thmb:
        widths_and_heights.append(thmb)
    return sorted(widths_and_heights)


def test_get_widths_and_heights_202203():
    """
    In order to understand how WordPress rounds... have a ton of examples.
    """
    # pip-options
    w, h = 728, 450
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 185)
    ]
    # az-vm-options
    w, h = 624, 298
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 143)
    ]
    # grade-a-server-daten-because-hsts
    w, h = 499, 329
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 198)
    ]
    # grade-a-ssllabs-no-hsts-no-redirect80
    w, h = 743, 477
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 193)
    ]
    # grade-b-server-daten-redirect-but-no-hsts
    w, h = 499, 285
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 171)
    ]
    # status.clouveo. webp
    w, h = 1020, 741
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 218),
        (768, 558)
    ]
    # lena_strip. webp
    w, h = 300, 1200
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (75, 300),
        (150, 150),
        (256, 1024)
    ]
    # ssllabs-ap-with-hsts-and-redirects
    w, h = 901, 499
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 166),
        (768, 425)
    ]


def test_get_widths_and_heights_202202():
    # compressioncomparison. webp
    w, h = 900, 1080
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (250, 300),
        (768, 922),
        (853, 1024),
    ]
    # flapjack_lifting. webp
    # The 768 width demonstrates direction of rounding expected, the
    # calculation comes to 520.5, so we expect 521. Python round gives 520.
    w, h = 1024, 694
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 203),
        (768, 521)
    ]


def test_get_widths_and_heights_202108():
    # steamed. webp
    w, h = 1032, 480
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 140),
        (768, 357),
        (1024, 476)
    ]
    # how-it-looked-installed
    w, h = 1080, 424
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 118),
        (768, 302),
        (1024, 402)
    ]
    # mitmproxy-screen
    w, h = 1219, 396
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 97),
        (768, 249),
        (1024, 333)
    ]


def test_get_widths_and_heights_202207():
    # Edge cases I hadn't previously explored.
    w, h = 1024, 200
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 59),
        (768, 150)
    ]

    w, h = 200, 1024
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (59, 300),
        (150, 150)
    ]

    w, h = 200, 300
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150)
    ]

    w, h = 300, 200
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150)
    ]

    w, h = 300, 400
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (225, 300)
    ]

    w, h = 400, 300
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 150),
        (300, 225)
    ]

    w, h = 768, 100
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150, 100),
        (300, 39)
    ]

    w, h = 100, 100
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == []


def test_get_widths_and_heights_v5_3():
    # Edge cases I hadn't previously explored.
    w, h = 2560, 1440
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150,150), (300,169), (768,432), (1024,576), (1536,864), (2048,1152)
    ]
    w, h = 4000, 3000
    # Thought (2560,1920) was used but apparently not:
    '''
testswhite_300x400.png
testswhite_4000x3000-1024x768.png
testswhite_4000x3000-150x150.png
testswhite_4000x3000-1536x1152.png
testswhite_4000x3000-2048x1536.png
testswhite_4000x3000-300x225.png
testswhite_4000x3000-768x576.png
testswhite_4000x3000.png
    '''
    widths_and_heights = combined_widths_and_heights(w, h)
    assert widths_and_heights == [
        (150,150), (300,225), (768,576), (1024,768), (1536,1152), (2048,1536)
    ]


def test_ResolutionsList_round_halves_up():
    assert ResolutionsList.round(0.5) == 1
    assert ResolutionsList.round(1.5) == 2
    assert ResolutionsList.round(2.5) == 3
    assert ResolutionsList.round(12.5) == 13
    assert ResolutionsList.round(101.5) == 102


def test_ResolutionsList_round():
    assert ResolutionsList.round(0.499) == 0
    assert ResolutionsList.round(0.501) == 1
    assert ResolutionsList.round(1.499) == 1
    assert ResolutionsList.round(1.501) == 2
    assert ResolutionsList.round(2.499) == 2
    assert ResolutionsList.round(2.501) == 3
    assert ResolutionsList.round(3.499) == 3
    assert ResolutionsList.round(3.501) == 4


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


