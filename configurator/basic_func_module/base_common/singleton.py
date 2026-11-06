# This Python file uses the following encoding: utf-8
############################################################################
# Copyright (c) 2025 Li Auto Inc. and its affiliates
# Licensed under the Apache License, Version 2.0(the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############################################################################
import threading

__all__ = ["Singleton"]


class SingletonMeta(type):
    """
    Metaclass for defining Singleton Meta Classes.
    """

    __instances = {}
    __lock = threading.RLock()

    def __call__(cls, *args, **kwargs):
        if cls in cls.__instances:
            return cls.__instances[cls]
        with cls.__lock:
            if cls not in cls.__instances:
                cls.__instances[cls] = super().__call__(*args, **kwargs)
            return cls.__instances[cls]

    @classmethod
    def get_instance(cls, class_obj):
        return cls.__instances.get(class_obj)


class Singleton(metaclass=SingletonMeta):
    """
    Helper class that provides a standard way to create an Singleton using inheritance.
    """

    pass


if __name__ == "__main__":

    class MyClass(Singleton):
        pass

    a = MyClass()
    b = MyClass()
    assert id(a) == id(b)
