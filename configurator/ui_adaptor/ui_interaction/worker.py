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
import sys
import atexit
import traceback
from PySide6 import QtCore
from PySide6.QtCore import Qt
from ui_adaptor.ui_interaction.progress_dialog import ProgressDialog
from ui_adaptor.ui_interaction.ui_logger import logger
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()
atexit.register(executor.shutdown, wait=True)


class WorkerSignals(QtCore.QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc())

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    """

    finished = QtCore.Signal()
    error = QtCore.Signal(tuple)
    result = QtCore.Signal(object)
    progress = QtCore.Signal(object)


class Task:
    """
    Worker thread

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    """

    progress_dialog = None
    is_debug = False
    active_tasks = {}

    def __init__(
        self,
        callback,
        *args,
        error_callback=None,
        result_callback=None,
        finished_callback=None,
        auto_run=True,
        enable_progress=True,
        **kwargs,
    ):
        super().__init__()

        # Store constructor arguments (re-used for processing)
        self.callback = callback
        self.auto_run = auto_run
        self.args = args
        self.kwargs = kwargs
        self.enable_progress = enable_progress
        self.signals = WorkerSignals()
        self.connection_type = QtCore.Qt.ConnectionType.QueuedConnection
        self.future = None
        if callable(error_callback):
            self.signals.error.connect(error_callback, self.connection_type)
        if callable(result_callback):
            self.signals.result.connect(result_callback, self.connection_type)
        if callable(finished_callback):
            self.signals.finished.connect(finished_callback, self.connection_type)
        self.signals.finished.connect(self.on_finished_cleanup, self.connection_type)
        if self.enable_progress:
            self.signals.progress.connect(self.update_progress, self.connection_type)
            # Add the progress_signal to our kwargs
            self.kwargs["progress_signal"] = self.signals.progress
            Task.progress_dialog = ProgressDialog()
            Task.progress_dialog.show()
        Task.active_tasks[id(self)] = self
        if auto_run:
            self.start()

    def update_progress(self, text):
        if not Task.progress_dialog:
            return
        if Task.progress_dialog.isHidden():
            Task.progress_dialog.show()
        Task.progress_dialog.setLabelText(str(text))

    def on_finished_cleanup(self):
        Task.active_tasks.pop(id(self), None)

    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        logger.set_auto_fresh()
        try:
            result = self.callback(*self.args, **self.kwargs)
        except BaseException:
            exctype, value, _ = sys.exc_info()
            if value and type(value).__name__ == "SystemExit" and len(value.args) > 0 and value.args[0] == 0:
                pass
            else:
                logger.ui_error("Task exception exit, Please check log file for details.")
            logger.exception("Task exception exit!")
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
            logger.cancle_auto_fresh()

    def start(self):
        if self.future:
            return
        self.future = executor.submit(self.run)
        self.future.add_done_callback(self.done)

    def stop(self):
        if self.future:
            self.future.cancel()

    def done(self, future):
        if Task.progress_dialog:
            QtCore.QMetaObject.invokeMethod(
                Task.progress_dialog,
                "hide",  # type: ignore
                Qt.ConnectionType(Qt.ConnectionType.QueuedConnection.value | Qt.ConnectionType.UniqueConnection.value),
            )
