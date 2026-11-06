import os
import chardet
import inspect
from lark.exceptions import UnexpectedInput
from ldfparser.parser import parse_ldf_to_dict
from basic_func_module.file_validation.file_validator import FileValidator
from basic_func_module.file_validation import ldf_semantic_rules


class EmptyFileError(Exception):

    def __init__(self) -> None:
        super().__init__()


class LdfValidator(FileValidator):

    def validate(self, file_path):

        def error_log(text: str):
            self._append_log(file_path, "ERROR", -1, text)

        if not os.path.exists(file_path):
            self._append_log(file_path, "ERROR", -1, "File not exist")
            return False

        res = True
        # Syntax validation
        try:
            encoding = "utf-8"
            with open(file_path, "rb") as f:
                encoding = chardet.detect(f.read())["encoding"]
            ldf_dict = parse_ldf_to_dict(file_path, encoding=encoding)
            # Empty file also cannot pass
            if not ldf_dict:
                raise EmptyFileError()
        except UnexpectedInput as e:
            res = False
            self._append_log(file_path, "ERROR", e.line, str(e))
        except EmptyFileError:
            res = False
            self._append_log(file_path, "ERROR", -1, "Empty file")
        else:
            # Semantic validation
            rules_dict = {
                member[0]: member[1]
                for member in inspect.getmembers(ldf_semantic_rules, ldf_semantic_rules.is_ldf_semantic_rule)
            }
            for func in rules_dict.values():
                res = res and func(ldf_dict, error_log)

        return res


if __name__ == "__main__":
    LDF_FILE = ""
    va = LdfValidator()
    res = va.validate(LDF_FILE)
