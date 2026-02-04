import os
import re
import sys
import types
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

LABELIMG_ROOT = Path(__file__).resolve().parents[2] / "third_party" / "labelImg"
RESOURCES_ROOT = LABELIMG_ROOT / "resources"
ICONS_DIR = RESOURCES_ROOT / "icons"
STRINGS_DIR = RESOURCES_ROOT / "strings"


def _ensure_labelimg_path():
    if str(LABELIMG_ROOT) not in sys.path:
        sys.path.insert(0, str(LABELIMG_ROOT))


def _ensure_resources_stub():
    if "libs.resources" not in sys.modules:
        sys.modules["libs.resources"] = types.ModuleType("libs.resources")


def _resolve_icon_path(icon_name):
    alias_map = {
        "help": "help.png",
        "app": "app.png",
        "expert": "expert2.png",
        "done": "done.png",
        "file": "file.png",
        "labels": "labels.png",
        "new": "objects.png",
        "close": "close.png",
        "fit-width": "fit-width.png",
        "fit-window": "fit-window.png",
        "undo": "undo.png",
        "hide": "eye.png",
        "quit": "quit.png",
        "copy": "copy.png",
        "edit": "edit.png",
        "open": "open.png",
        "save": "save.png",
        "format_voc": "format_voc.png",
        "format_yolo": "format_yolo.png",
        "format_createml": "format_createml.png",
        "save-as": "save-as.png",
        "color": "color.png",
        "color_line": "color_line.png",
        "zoom": "zoom.png",
        "zoom-in": "zoom-in.png",
        "zoom-out": "zoom-out.png",
        "light_reset": "light_reset.png",
        "light_lighten": "light_lighten.png",
        "light_darken": "light_darken.png",
        "delete": "cancel.png",
        "next": "next.png",
        "prev": "prev.png",
        "resetall": "resetall.png",
        "verify": "verify.png",
    }

    filename = alias_map.get(icon_name)
    if filename:
        candidate = ICONS_DIR / filename
        if candidate.exists():
            return candidate

    for ext in (".png", ".svg", ".ico"):
        candidate = ICONS_DIR / f"{icon_name}{ext}"
        if candidate.exists():
            return candidate

    return None


def _new_icon(icon_name):
    path = _resolve_icon_path(icon_name)
    return QIcon(str(path)) if path else QIcon()


def _patch_string_bundle(label_string_bundle):
    def _create_lookup_fallback_list(self, locale_str):
        result_paths = []
        base_path = STRINGS_DIR / "strings"
        result_paths.append(str(base_path))
        if locale_str is not None:
            tags = re.split("[^a-zA-Z]", locale_str)
            for tag in tags:
                last_path = result_paths[-1]
                result_paths.append(last_path + "-" + tag)
        return result_paths

    def _load_bundle(self, path):
        filename = f"{path}.properties"
        if not os.path.exists(filename):
            return
        with open(filename, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                key_value = line.split("=")
                key = key_value[0].strip()
                value = "=".join(key_value[1:]).strip().strip('"')
                self.id_to_message[key] = value

    label_string_bundle.StringBundle._StringBundle__create_lookup_fallback_list = _create_lookup_fallback_list
    label_string_bundle.StringBundle._StringBundle__load_bundle = _load_bundle


def _patch_utils(label_utils):
    label_utils.new_icon = _new_icon


def _apply_labelimg_patches():
    _ensure_labelimg_path()
    _ensure_resources_stub()

    from libs import stringBundle as label_string_bundle
    from libs import utils as label_utils

    if "libs" in sys.modules and "libs.resources" in sys.modules:
        setattr(sys.modules["libs"], "resources", sys.modules["libs.resources"])

    _patch_string_bundle(label_string_bundle)
    _patch_utils(label_utils)


_apply_labelimg_patches()

import labelImg as labelimg_module

labelimg_module.__appname__ = "FluentLabel"


class AnnotationWindow(labelimg_module.MainWindow):
    def __init__(
        self,
        default_filename=None,
        default_prefdef_class_file=None,
        default_save_dir=None,
        parent=None,
    ):
        if default_prefdef_class_file is None:
            default_prefdef_class_file = str(LABELIMG_ROOT / "data" / "predefined_classes.txt")

        super().__init__(default_filename, default_prefdef_class_file, default_save_dir)

        if parent is not None:
            self.setParent(parent)
            self.setWindowFlags(Qt.Widget)
