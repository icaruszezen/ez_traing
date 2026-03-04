import re
import os
import sys
import locale
from pathlib import Path

from ez_traing.labeling.ustr import ustr

if getattr(sys, "frozen", False):
    _LABELING_ROOT = Path(sys._MEIPASS) / "ez_traing" / "labeling"
else:
    _LABELING_ROOT = Path(__file__).resolve().parent

STRINGS_DIR = _LABELING_ROOT / "resources" / "strings"


class StringBundle:

    __create_key = object()

    def __init__(self, create_key, locale_str):
        assert (create_key == StringBundle.__create_key), \
            "StringBundle must be created using StringBundle.getBundle"
        self.id_to_message = {}
        paths = self.__create_lookup_fallback_list(locale_str)
        for path in paths:
            self.__load_bundle(path)

    @classmethod
    def get_bundle(cls, locale_str=None):
        if locale_str is None:
            try:
                locale_str = locale.getdefaultlocale()[0] if locale.getdefaultlocale() and len(
                    locale.getdefaultlocale()) > 0 else os.getenv('LANG')
            except Exception:
                print('Invalid locale')
                locale_str = 'en'

        return StringBundle(cls.__create_key, locale_str)

    def get_string(self, string_id):
        assert (string_id in self.id_to_message), "Missing string id : " + string_id
        return self.id_to_message[string_id]

    def __create_lookup_fallback_list(self, locale_str):
        result_paths = []
        base_path = str(STRINGS_DIR / "strings")
        result_paths.append(base_path)
        if locale_str is not None:
            tags = re.split('[^a-zA-Z]', locale_str)
            for tag in tags:
                last_path = result_paths[-1]
                result_paths.append(last_path + '-' + tag)
        return result_paths

    def __load_bundle(self, path):
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
