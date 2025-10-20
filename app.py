import tkinter as tk
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from components import UISetup, EventHandlers, MessageProcessor
from core import ModelManager, AudioManager, RecordingManager
class SpeechToTextApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Распознавание речи в реальном времени")
        self.root.geometry("850x750")
        self.root.resizable(True, True)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.audio_queue = queue.Queue(maxsize=10)
        self.ui_queue = queue.Queue()
        self.model_manager = ModelManager()
        self.audio_manager = AudioManager()
        self.recording_manager = RecordingManager(self.audio_manager, self.model_manager)
        self.ui_setup = UISetup()
        self.event_handlers = EventHandlers(self)
        self.message_processor = MessageProcessor(self)
        self.is_recording = False
        self.recording_thread = None
        self.processing_thread = None
        self.stop_flags = {
            'recording': threading.Event(),
            'processing': threading.Event()
        }
        self.ui_elements = {}
        self.setup_ui()
        self.setup_bindings()
        self.start_message_processing()
    def setup_ui(self):
        self.ui_elements = self.ui_setup.create_interface(self.root, self)
    def setup_bindings(self):
        self.event_handlers.setup_bindings()
    def start_message_processing(self):
        self.message_processor.start_processing()
    def select_model(self):
        return self.event_handlers.handle_model_selection()
    def start_recording(self):
        return self.event_handlers.handle_start_recording()
    def stop_recording(self):
        return self.event_handlers.handle_stop_recording()
    def clear_text(self):
        return self.event_handlers.handle_clear_text()
    def clear_logs(self):
        return self.event_handlers.handle_clear_logs()
    def update_text(self, text):
        return self.message_processor.update_text_display(text)
    def queue_ui_message(self, msg_type, title="", message="", **kwargs):
        return self.message_processor.queue_message(msg_type, title, message, **kwargs)
    def cleanup(self):
        self.stop_recording()
        self.executor.shutdown(wait=False)
        self.audio_manager.cleanup()
    def __del__(self):
        self.cleanup()
    def copy_selected_text_universal(self):
        try:
            focused_widget = self.root.focus_get()
            if focused_widget and hasattr(focused_widget, 'tag_ranges'):
                if focused_widget.tag_ranges(tk.SEL):
                    selected_text = focused_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                    self.root.clipboard_clear()
                    self.root.clipboard_append(selected_text)
        except Exception as e:
            print(f"Ошибка копирования: {e}")
    def select_all_text_universal(self):
        try:
            focused_widget = self.root.focus_get()
            if focused_widget and hasattr(focused_widget, 'tag_add'):
                focused_widget.tag_add(tk.SEL, "1.0", tk.END)
                focused_widget.mark_set(tk.INSERT, "1.0")
                focused_widget.see(tk.INSERT)
                focused_widget.focus_set()
        except Exception as e:
            print(f"Ошибка выделения: {e}")
    def copy_text_from_widget(self, widget):
        try:
            if widget.tag_ranges(tk.SEL):
                selected_text = widget.selection_get()
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
            else:
                widget.config(state=tk.NORMAL)
                all_text = widget.get(1.0, tk.END)
                widget.config(state=tk.DISABLED)
                self.root.clipboard_clear()
                self.root.clipboard_append(all_text.strip())
        except tk.TclError:
            pass
    def select_all_from_widget(self, widget):
        try:
            widget.config(state=tk.NORMAL)
            widget.tag_add(tk.SEL, "1.0", tk.END)
            widget.mark_set(tk.INSERT, "1.0")
            widget.see(tk.INSERT)
            widget.focus_set()
            widget.config(state=tk.DISABLED)
        except tk.TclError:
            pass