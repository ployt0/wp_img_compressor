#!/usr/bin/env python3
"""
Requires a working image magick installation.
I am aware Wand https://docs.wand-py.org/en/0.6.8/ is the python interface
to ImageMagick, but not only does that require ImageMagick, it also
requires ImageMagick-devel, is yet another dependency and obfuscates
the command lines used to prototype/learn the operations performed.

To offer the use a choice/appraisal of the compression mechanisms we might
make an html gallery, and pause waiting for the user to approve one so we
can delete the rest.

Or we could use install pillow (about 12MB) or matplotlib together with
numpy (about 130MB).

The advantage of pillow is that each image is a different window and so it
is easy to discard outliers. But that is all the interaction the default
image viewer guarantees. We can at least annotate images if the file name
isn't specific enough: https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html
https://web.archive.org/web/20200705080256id_/http://effbot.org/imagingbook/introduction.htm#postscript-printing
The disadvantage of PIL is that, standalone, it writes a temporary image to
disk to share with the viewer application. This is the behaviour of `show`
which it describes as for debugging purposes https://pillow.readthedocs.io/en/stable/handbook/overview.html#image-display
Not only is that wasteful of writes, but it casts doubt on the accuracy of
the presentation we may well be pixel peeping.

The preferred way of displaying images in PIL is with tkinter. Which is a
whole GUI frontend in itself and I don't think it plays well with virtual
environments. `pip install tk` appears to succeed but the venv is only 1MB
bigger and I can't do anything (eg `tk.Label(...)`) with it. Frontends are
heavier.

"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path
import subprocess
from typing import List, Tuple, Any, Dict
from decimal import Decimal, ROUND_HALF_UP

import requests.exceptions
from jinja2 import Template

# print(sys.path)

from paramiko_client import get_client, execute_remotely, filter_dict_for_creds
from wp_api.api_app import WP_API


class CompressorException(Exception):
    pass


def run_shell_cmd(cmd: List[str]):
    result = subprocess.run(cmd, capture_output=True)
    result_text = None
    if result.returncode == 0:
        result_text = result.stdout.decode()
    return result_text


def get_file_size(file_name: str):
    result_text = run_shell_cmd(['stat', '-c' '%s %n', file_name])
    return result_text.split()[0]


def get_img_wxh(file_name: str):
    result_text = run_shell_cmd(['identify', '-ping', '-format', '"%wx%h"', file_name])
    return list(map(int, result_text.strip("\"").split("x")))


class ResolutionsList(list):
    @staticmethod
    def round(a) -> int:
        """Rounding, as performed in WordPress, the "traditional" way."""
        return int(Decimal(a).quantize(0, ROUND_HALF_UP))

    def append(self, resolution: Tuple):
        rounded_resolution = (
            ResolutionsList.round(resolution[0]),
            ResolutionsList.round(resolution[1]))
        list.append(self, rounded_resolution)


DimsList = List[Tuple[int, int]]


def get_widths_and_heights(
        src_w: int, src_h: int,
        med_w: int=300, med_h: int=300,
        large_w: int=1024, large_h: int=1024,
        thumb_w: int=150, thumb_h: int=150) -> \
        Tuple[DimsList, Tuple[int, int]]:
    """
    WordPress media settings contain a lot of options for various sizes.
    These apply only at upload time (if at all), pre-existing images
    are not affected by changes to those parameters. There are defaults
    because I don't believe the vast majority of WordPress users appreciate,
    notice, or alter these.

    :param src_w: source width
    :param src_h: source height
    :param med_w: medium width
    :param med_h: medium height
    :param large_w: large width
    :param large_h: large height
    :param thumb_w: thumbnail width
    :param thumb_h: thumbnail height
    :return: 2-tuple of generated sizes and a separate thumbnail size, if
        applicable, because that is zoom cropped unlike the rest.
    """
    MED_LARGE_W = 768
    w_hs = ResolutionsList()
    # 768 isn't optional!
    if src_w > MED_LARGE_W:
        w_hs.append(fix_width(src_h, src_w, MED_LARGE_W))
    thmb = get_thumbnail(src_w, src_h, thumb_w, thumb_h)
    add_scaled_size_bounded_by(w_hs, src_w, src_h, med_w, med_h)
    add_scaled_size_bounded_by(w_hs, src_w, src_h, large_w, large_h)
    # WordPress v.5.3 introduced three new large resized image sizes
    # https://wpo.plus/wordpress/large-image-sizes/
    # Currently, these are "named": "1536x1536" and "2048x2048" in the SQL.
    # I haven't seen a 2560 yet!
    add_scaled_size_bounded_by(w_hs, src_w, src_h, 1536, 1536)
    add_scaled_size_bounded_by(w_hs, src_w, src_h, 2048, 2048)
    add_scaled_size_bounded_by(w_hs, src_w, src_h, 2560, 2560)
    return sorted(w_hs), thmb


def get_thumbnail(src_w: int, src_h: int, thumb_w: int, thumb_h: int):
    if src_w >= thumb_w or src_h >= thumb_h:
        # This, thumbnail, is the only cropping transform (by default).
        # The other size all scale instead.
        if src_w < thumb_w and src_h < thumb_h:
            return
        if src_w < thumb_w:
            thumb_w = src_w
        if src_h < thumb_h:
            thumb_h = src_h
        return thumb_w, thumb_h


def add_scaled_size_bounded_by(w_hs: ResolutionsList, src_w: int, src_h: int, max_w: int, max_h: int):
    if src_w > max_w or src_h > max_h:
        w_over = float(src_w) / max_w
        h_over = float(src_h) / max_h
        constraint = max(w_over, h_over)
        w_hs.append((src_w / constraint, src_h / constraint))


def fix_width(src_h: int, src_w: int, fixed_width: int) -> Tuple[int, int]:
    return fixed_width,\
           ResolutionsList.round(float(src_h) * fixed_width / src_w)


def fix_height(src_h: int, src_w: int, fixed_height: int) -> Tuple[int, int]:
    return ResolutionsList.round(float(src_w) * fixed_height / src_h),\
           fixed_height


def split_cmd_not_args(f_str_vars: Dict[str, Any], cmd: str) -> List[str]:
    """
    subprocess.run likes the split string format best.
    Sure we could separate arguments from the command too.

    :param f_str_vars: dictionary of arguments to the f string.
    :param cmd: the command including f-string place holders.
    :return: list of input tokens.
    """
    curlied_dict = {"{" + k + "}": str(v) for k,v in f_str_vars.items()}
    rebuilt_cmd = []
    for token in cmd.split():
        for k, v in curlied_dict.items():
            token = token.replace(k, v)
        rebuilt_cmd.append(token)
    return rebuilt_cmd


def get_name_decor(w: int, h: int, ext: str):
    return '-{}x{}.{}'.format(w, h, ext)


class ImgConvertor:
    """
    Subclasses should wrap the IMagick calls that process their respective
    image type.
    """
    def __init__(self, img_name: str,
                 widths_and_heights: DimsList,
                 subdir_root: str):
        """
        :param img_name: absolute or relative path of source image.
        :param widths_and_heights: the thumbnail is excluded.
        :param subdir_root: can be empty, but if something, / will be appended
            if not already
        """
        self.img_name = img_name
        self.stem_name = Path(self.img_name).stem
        self.widths_and_heights = widths_and_heights
        self.subdir_root = subdir_root
        if subdir_root and not subdir_root.endswith("/"):
            self.subdir_root  += "/"
        # Each *must* begin with the image format extension of its contents.
        self.all_dirs = []

    def path_to_resized_img(self, w: int, h: int, ext: str):
        return '{}{}{}{}'.format(
            self.subdir_name, os.path.sep, self.stem_name,
            get_name_decor(w, h, ext))

    def path_to_new_img(self, ext: str):
        return '{}{}{}.{}'.format(
            self.subdir_name, os.path.sep, self.stem_name, ext)

    def count_bytes_in_subdir(self) -> int:
        total_b = 0
        for entry in os.scandir(self.subdir_name):
            if entry.is_file():
                total_b += entry.stat().st_size
        return total_b

    def get_gallery_list(self, widths_and_heights: list, src_w: int, src_h: int):
        """
        The gallery list returned is prettified to headings for
        each subdirectory followed by a list of *representative* images'
        paths for that folder.

        This was chosen to include the full scale image and the smallest images
        only, though perhaps full scale isn't as representative as the largest
        version if it is missing a scaling operation we may be interested in.
        """
        gallery_list = []
        for total_b, fqdir in sorted(self.all_dirs):
            dir_name, suffix = self.extract_final_dir_and_suffix(fqdir)
            gallery_item = ["{}KB {}: {}x{}".format(
                round(total_b / 1024), dir_name,
                src_w, src_h),
                ['{}{}{}.{}'.format(
                    fqdir, os.path.sep, self.stem_name, suffix)]]
            gallery_list.append(gallery_item)
            if widths_and_heights:
                gallery_item[0] += " > {}x{}".format(
                    widths_and_heights[0][0], widths_and_heights[0][1])
                gallery_item[1].append(
                    '{}{}{}-{}x{}.{}'.format(
                        fqdir, os.path.sep, self.stem_name,
                        widths_and_heights[0][0],
                        widths_and_heights[0][1],
                        suffix
                    ))
        return gallery_list

    def extract_final_dir_and_suffix(self, fqdir_name: str):
        """
        :param fqdir_name: must be the direct child of self.subdir_root.
        :return: the name of just the dir child *AND* the image extension
            with which it starts.
        """
        dir_name = fqdir_name[len(self.subdir_root):]
        suffix = dir_name.split("_")[0]
        return dir_name, suffix

    def print_summary(self) -> List[Tuple[int, str]]:
        size_list = list(sorted(self.all_dirs))
        for i, item in enumerate(size_list):
            print("{:2}: {}KB, {}".format(
                i, round(item[0] / 1024), item[1][len(self.subdir_root):]))
        return size_list

    def present_gallery(self, w, h, widths_and_heights):
        gallery_list = self.get_gallery_list(widths_and_heights, w, h)
        template_file = os.path.join(
            Path(__file__).parent.resolve(), "gallery_template.html")
        with open(template_file) as f_in:
            template = Template(f_in.read())
        with open("gallery.html", "w") as f_out:
            f_out.write(template.render(
                {"galleryList": gallery_list}
            ))
        print("Please review the results at file:"
              "//{} and select the set you prefer."
              .format(str(Path("gallery.html").resolve()),
                      str(Path("gallery.html").resolve())))

    def select_one(self) -> str:
        """
        :return: Chosen directory path, relative or absolute, as defined by the
            subdir_root which precedes it.
        """
        if len(self.all_dirs) == 0:
            raise CompressorException("self.all_dirs is empty, aborting.")
        size_list = self.print_summary()
        choice = int(
            input("Choose [0-{}]: ".format(len(self.all_dirs) - 1)))
        while choice < 0 or choice >= len(self.all_dirs):
            self.print_summary()
            choice = int(
                input("Choose [0-{}]: ".format(len(self.all_dirs) - 1)))
        chosen_dir = size_list[choice][1]
        return chosen_dir

    def upload(self, chosen_generated_dir: str, conf_file: str):
        """
        
        :param chosen_generated_dir: relative or absolute, as defined by the
            subdir_root which precedes it. 
        :param conf_file: credentials for API and SSH/SCP
        :return:
        """
        self.subdir_name = chosen_generated_dir
        suffix = self.extract_final_dir_and_suffix(chosen_generated_dir)[1]
        singular_source = os.path.join(
            chosen_generated_dir, self.stem_name + "." + suffix)
        print("Uploading {}".format(singular_source))
        wp_api = WP_API(conf_file)
        # All kinds of juicy details to save intrusive paramiko.
        media_details = wp_api.upload_media(singular_source).json()["media_details"]
        with open(conf_file) as f:
            conf = json.load(f)["ssh"]
        host, port = conf["host"], 22
        if ":" in host:
            host, port = host.split(":")
        self.replace_generated_sizes(
            host, port, filter_dict_for_creds(conf), suffix,
            os.path.join(conf["wp_uploads"], media_details["file"]))

    def replace_generated_sizes(self, host, port, credentials: dict, suffix,
                                fq_rmt_path: str):
        client = get_client(host, int(port), credentials)
        sftp = None
        try:
            stdout, _ = execute_remotely(client, "mkdir -p /tmp/stagingtmp")
            rmt_dir = Path(fq_rmt_path).parent.resolve()
            sftp = client.open_sftp()
            for w, h in self.widths_and_heights:
                # This should overwrite all the shrunk images WP made, except
                # the 150x150 thumbnail.
                src_name = str(Path(self.path_to_resized_img(w, h, suffix)).resolve())
                base_rmt_name = Path(fq_rmt_path).stem + get_name_decor(w, h, suffix)
                final_name = "{}/{}".format(rmt_dir, base_rmt_name).replace("//", "/")
                sftp.put(src_name, "/tmp/stagingtmp/{}".format(base_rmt_name))
                # Sequence these to avoid the race hazard of chown'ing before
                # overwriting:
                stdout, stderr = execute_remotely(
                    client,
                    "sudo mv /tmp/stagingtmp/{base_rmt_name} {final_name} && "
                    "sudo chown www-data:www-data {final_name}".format(
                        base_rmt_name=base_rmt_name, final_name=final_name))
                if stderr:
                    raise RuntimeError(stderr)
            sftp.close()
            client.close()
        except Exception as e:
            if sftp:
                sftp.close()
            if client:
                client.close()
            raise

    def transform_to_dir(self, q, suffix: str, descriptive: str,
                         unscaled_cmd: str, scaling_cmds: List[str]) -> None:
        """
        Supply a single line string for the unscaled operation and any number of
        lines for the scaling operations. We use f-string (py 3.6) and you can
        find the available variable substitutions in the code below.

        :param q: q, either quality or quantisations.
        :param suffix: for subdirectory and output images.
        :param descriptive: name for subdirectory for all outputs below.
        :param unscaled_cmd: single line for unscaled conversion.
        :param scaling_cmds: multi-line command for scaled conversion.
        :return:
        """
        self.subdir_name = os.path.join(
            self.subdir_root, "{}_q{}_{}".format(suffix, q, descriptive))
        Path(self.subdir_name).mkdir(parents=True, exist_ok=True)

        suffix = self.extract_final_dir_and_suffix(self.subdir_name)[-1]
        f_str_vars = {
            "q": q,
            "src_img": self.img_name,
            "tmp_img": os.path.join(self.subdir_name, "tmp.png"),
            "tmp_img2": os.path.join(self.subdir_name, "tmp2.png"),
            "dest_img": self.path_to_new_img(suffix)
        }
        split_cmd = split_cmd_not_args(f_str_vars, unscaled_cmd)
        run_shell_cmd(split_cmd)
        for w, h in self.widths_and_heights:
            for scaling_cmd in scaling_cmds:
                split_cmd = split_cmd_not_args({
                    "w": w,
                    "h": h,
                    "resized_img": self.path_to_resized_img(w, h, suffix),
                    **f_str_vars
                }, scaling_cmd)
                run_shell_cmd(split_cmd)
        Path(f_str_vars["tmp_img"]).unlink(missing_ok=True)
        Path(f_str_vars["tmp_img2"]).unlink(missing_ok=True)
        self.all_dirs.append((self.count_bytes_in_subdir(), self.subdir_name))


def resize(
        img_name: str,
        conf_file: str = "config.json",
        skip_jpg: bool=True, skip_png: bool=False, skip_webp: bool=False,
        fullsize_only: bool=False):
    """
    300 (medium) and 1024 (large) are maximums that the largest dimension takes.
    These, and thumbnail, sizes are configurable through the WP UI.
    I haven't ever beaten how WP makes its 150x150 (thumbnail). I don't have an
    algorithm or POC to do the zoom crop WP does either.

    768 (medium_large) is a fixed width chosen by WordPress not us.

    :param img_name: absolute or relative path of source image
    :param conf_file: path to config json with keys "ssh" and "api".
    :param skip_jpg: don't explore jpg output options
    :param skip_png: don't explore png output options
    :param skip_webp: don't explore webp output options
    :param fullsize_only: to extend the use beyond WordPress, don't generate
        resized images, instead apply algo's only to the full size image.
    :return:
    """
    if not os.path.isfile(img_name):
        fqfnm = Path(img_name).resolve()
        raise FileNotFoundError("\"{}\" not found. Looking for: \"{}\".".format(img_name, fqfnm))
    if img_name.split(".")[-1] not in ["png", "jpg", "jpeg", "webp"]:
        raise RuntimeError("Unknown image file type: \"{}\"".format(img_name))

    w, h = get_img_wxh(img_name)
    widths_and_heights, _ = get_widths_and_heights(w, h)
    subdir_root = "tmp/"
    img_processor = ImgConvertor(img_name, widths_and_heights, subdir_root)
    if not skip_png:
        # PNG to PNG is lossless so even if we've already quantized before,
        # we can recover the efficiently resized versions losslessly here.
        for q in [255, 128, 64, 32, 16]:
            if fullsize_only:
                img_processor.transform_to_dir(
                    q, "png", "no_resize",
                    "convert -strip -colors {q} {src_img} {dest_img}",
                    [],
                )
            else:
                img_processor.transform_to_dir(
                    q, "png", "inc_resize",
                    "convert -strip -colors {q} {src_img} {dest_img}",
                    ["convert -strip -resize {w}x{h} -colors {q} {src_img} {resized_img}"],
                )
                img_processor.transform_to_dir(
                    q, "png", "aft_resize",
                    "convert -strip -colors {q} {src_img} {dest_img}",
                    ["convert -strip -resize {w}x{h} {src_img} {tmp_img}",
                    "convert -strip -colors {q} {tmp_img} {resized_img}"]
                )
    for q in [80, 70, 60, 50]:
        if not skip_jpg:
            if fullsize_only:
                img_processor.transform_to_dir(
                    q, "jpg", "no_resize",
                    "convert -strip -interlace Plane -gaussian-blur 0.05 -quality {q} {src_img} {dest_img}",
                    []
                )
            else:
                img_processor.transform_to_dir(
                    q, "jpg", "inc_resize",
                    "convert -strip -interlace Plane -gaussian-blur 0.05 -quality {q} {src_img} {dest_img}",
                    ["convert -strip -resize {w}x{h} -interlace Plane -gaussian-blur 0.05 -quality {q} {src_img} {resized_img}"]
                )
        if not skip_webp:
            if fullsize_only:
                img_processor.transform_to_dir(
                    q, "webp", "no_resize",
                    "convert -strip -define webp:method=6 -quality {q} {src_img} {dest_img}",
                    []
                )
            else:
                img_processor.transform_to_dir(
                    q, "webp", "inc_resize",
                    "convert -strip -define webp:method=6 -quality {q} {src_img} {dest_img}",
                    ["convert -strip -resize {w}x{h} -define webp:method=6 -quality {q} {src_img} {resized_img}"]
                )

    process_outputs(w, h, img_processor, widths_and_heights, conf_file)


def process_outputs(
        w, h, img_processor: ImgConvertor, widths_and_heights, conf_file: str):
    img_processor.present_gallery(w, h, widths_and_heights)
    chosen_generated_dir = img_processor.select_one()
    try:
        img_processor.upload(chosen_generated_dir, conf_file)
    except requests.exceptions.ConnectionError as rex_conn:
        delete_other_dirs(chosen_generated_dir, img_processor)
        raise ConnectionError("Uploading failed. Requests says: \"{}\"".format(rex_conn))
    except FileNotFoundError as fnferr:
        # Likely the user didn't bother with config.json
        delete_other_dirs(chosen_generated_dir, img_processor)
        raise
    else:
        shutil.rmtree(img_processor.subdir_root)


def delete_other_dirs(chosen_generated_dir, img_processor):
    for a_dir in img_processor.all_dirs:
        if a_dir[1] != chosen_generated_dir:
            shutil.rmtree(a_dir[1])


def process_args(args_list: List[str]):

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""Image manipulation for WordPress.

Tries out various optimisations to shrink the footprint of the resized copies
WordPress likes to make when any image is uploaded to it.

Uses wp_api.api_app which will need your API credentials in a config.json,
on the subject of which we may as well add the SSH credentials there too:

{
  "api": {
    "host_url": "https://localhost:6666",
    "user": "FRED_TEST",
    "password": "alls here bees prnt able F00B",
    "cert_name": "path/to/tls/cert/or/absent"
  },
  "ssh": {
    "host": "127.0.0.1:6667",
    "username": "vagrant",
    "password": "password",
    "key_filename": "../../.vagrant/machines/default/virtualbox/private_key"
    "wp_uploads": "/var/www/html/wp-content/uploads/"
  }
}

The API password is an application password because I don't want 2FA in this
script. The user must be at least an Author but authorship is attributed to 
media like it is to posts. However, I think this is only apparent to privileged
users who access the media library web page. It might be wise using an 
application password for the user you normally post from, or an
image_uploader_bot. For most cases the test_bot account will be fine.
""")
    parser.add_argument(
        "src_img",
        help="Name of source image that should be uploaded to WordPress.")
    parser.add_argument(
        "-j", "--skip_jpg_generation",
        help="Don't bother producing jpeg outputs as it has largely been superseded by webp.",
        action="store_true")
    parser.add_argument(
        "-p", "--skip_png_generation",
        help="Don't bother producing png outputs as they aren't efficient for photos.",
        action="store_true")
    parser.add_argument(
        "-w", "--skip_webp_generation",
        help="Don't bother producing webp outputs as they were only recently introduced.",
        action="store_true")
    parser.add_argument(
        "-f", "--fullsize_only",
        help="Don't resize the original, produce only full size copies.",
        action="store_true")
    parser.add_argument(
        "-c", "--config_file",
        help="Name of json file describing containing WordPress credentials.",
        default="config.json")
    args = parser.parse_args(args_list)
    resize(
        args.src_img,
        args.config_file,
        args.skip_jpg_generation,
        args.skip_png_generation,
        args.skip_webp_generation,
        args.fullsize_only
    )


def main(args_list: List[str]):
    process_args(args_list)


if __name__ == "__main__":
    main(sys.argv[1:])
