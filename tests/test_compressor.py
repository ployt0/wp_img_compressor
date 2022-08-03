from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest
import requests

from compressor import resize, process_args, process_outputs, process_outputs


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
@patch("compressor.cmn.get_img_wxh", return_value=[640, 480])
@patch("compressor.ImgScaler", autospec=True)
def test_resize(mock_scaler, mock_get_1wh, mock_process_outputs,
                mock_isfile, mock_img_conv):
    mock_scaler.return_value.get_widths_and_heights = Mock(return_value=(sentinel.widths_and_heights, sentinel.thumbnail))
    img_name = "this is a file path and name.jpg"
    resize(img_name, "config.json", False, False, False)
    mock_process_outputs.assert_called_once_with(
        640, 480, mock_img_conv.return_value, sentinel.widths_and_heights, "config.json"
    )
    mock_get_1wh.assert_called_once_with(img_name)
    mock_scaler.assert_called_once_with(640, 480)
    mock_scaler.return_value.get_widths_and_heights.assert_called_once_with()
    mock_isfile.assert_called_once_with(img_name)
    mock_img_conv.assert_called_once_with(img_name, sentinel.widths_and_heights, "tmp/")


@patch("compressor.ImgConvertor", autospec=True)
@patch("compressor.os.path.isfile", autospec=True, return_value=True)
@patch("compressor.process_outputs", autospec=True)
@patch("compressor.cmn.get_img_wxh", return_value=[640, 480])
@patch("compressor.ImgScaler", autospec=True)
def test_resize_fullsize_only(
        mock_scaler, mock_get_1wh, mock_process_outputs, mock_isfile,
        mock_img_conv):
    mock_scaler.return_value.get_widths_and_heights = Mock(return_value=(sentinel.widths_and_heights, sentinel.thumbnail))
    img_name = "this is a file path and name.jpg"
    resize(img_name, "config.json", False, False, False, True)
    mock_process_outputs.assert_called_once_with(
        640, 480, mock_img_conv.return_value, sentinel.widths_and_heights, "config.json"
    )
    mock_get_1wh.assert_called_once_with(img_name)
    mock_scaler.assert_called_once_with(640, 480)
    mock_scaler.return_value.get_widths_and_heights.assert_called_once_with()
    mock_isfile.assert_called_once_with(img_name)
    mock_img_conv.assert_called_once_with(img_name, sentinel.widths_and_heights, "tmp/")


@patch("compressor.shutil.rmtree", autospec=True)
@patch("compressor.ImgConvertor", autospec=True)
def test_process_outputs(mock_img_conv, mock_rmtree):
    mock_img_conv.return_value.subdir_root = sentinel.subdir_root
    mock_img_conv.return_value.all_dirs = sentinel.all_dirs
    process_outputs(20, 42, mock_img_conv.return_value, sentinel.widths_and_heights, sentinel.file_name)
    mock_img_conv.return_value.present_gallery.assert_called_once_with(20, 42, sentinel.widths_and_heights)
    mock_img_conv.return_value.select_one.assert_called_once_with()
    mock_img_conv.return_value.upload.assert_called_once_with(
        mock_img_conv.return_value.select_one.return_value,
        sentinel.file_name
    )
    mock_rmtree.assert_called_once_with(sentinel.subdir_root)
    mock_img_conv.return_value.delete_other_dirs.assert_not_called()


@patch("compressor.shutil.rmtree", autospec=True)
@patch("compressor.ImgConvertor", autospec=True)
def test_process_outputs_bad_upload(mock_img_conv, mock_rmtree):
    mock_img_conv.return_value.upload.side_effect = requests.exceptions.ConnectionError
    with pytest.raises(ConnectionError) as connerr:
        process_outputs(20, 42, mock_img_conv.return_value, sentinel.widths_and_heights, sentinel.file_name)
    mock_img_conv.return_value.present_gallery.assert_called_once_with(20, 42, sentinel.widths_and_heights)
    mock_img_conv.return_value.select_one.assert_called_once_with()
    mock_img_conv.return_value.upload.assert_called_once_with(
        mock_img_conv.return_value.select_one.return_value,
        sentinel.file_name
    )
    mock_rmtree.assert_not_called()
    mock_img_conv.return_value.delete_other_dirs.assert_called_once_with(
        mock_img_conv.return_value.select_one.return_value,
    )


@patch("compressor.shutil.rmtree", autospec=True)
@patch("compressor.ImgConvertor", autospec=True)
def test_process_outputs_bad_path(mock_img_conv, mock_rmtree):
    mock_img_conv.return_value.upload.side_effect = FileNotFoundError
    with pytest.raises(FileNotFoundError) as connerr:
        process_outputs(20, 42, mock_img_conv.return_value, sentinel.widths_and_heights, sentinel.file_name)
    mock_img_conv.return_value.present_gallery.assert_called_once_with(20, 42, sentinel.widths_and_heights)
    mock_img_conv.return_value.select_one.assert_called_once_with()
    mock_img_conv.return_value.upload.assert_called_once_with(
        mock_img_conv.return_value.select_one.return_value,
        sentinel.file_name
    )
    mock_rmtree.assert_not_called()
    mock_img_conv.return_value.delete_other_dirs.assert_called_once_with(
        mock_img_conv.return_value.select_one.return_value,
    )


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


