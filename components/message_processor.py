import tkinter as tk
from tkinter import messagebox as mb
import datetime
class MessageProcessor:
    def __init__(self, app):
        self.app = app
    def start_processing(self):
        self._process_queue()
    def _process_queue(self):
        try:
            while True:
                msg_type, title, message, kwargs = self.app.ui_queue.get_nowait()
                self._handle_message(msg_type, title, message, **kwargs)
        except:
            pass
        finally:
            self.app.root.after(100, self._process_queue)
    def _handle_message(self, msg_type, title, message, **kwargs):
        ui_elements = self.app.ui_elements
        if msg_type == "log":
            self._add_log_message(message)
        elif msg_type == "status":
            ui_elements['status_label'].config(text=message, **kwargs)
        elif msg_type == "text":
            self.update_text_display(message)
        elif msg_type == "model_info":
            ui_elements['model_info_label'].config(text=message)
        elif msg_type == "error":
            mb.showerror(title, message)
        elif msg_type == "info":
            mb.showinfo(title, message)
        elif msg_type == "enable_buttons":
            ui_elements['btn_start'].config(state=kwargs.get('start', tk.NORMAL))
            ui_elements['btn_stop'].config(state=kwargs.get('stop', tk.NORMAL))
    def _add_log_message(self, message):
        log_area = self.app.ui_elements['log_area']
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        log_area.config(state=tk.NORMAL)
        log_area.insert(tk.END, log_entry)
        log_area.config(state=tk.DISABLED)
        log_area.see(tk.END)
        log_area.update_idletasks()
        print(log_entry.strip())
    def update_text_display(self, text):
        text_area = self.app.ui_elements['text_area']
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_text = f"[{timestamp}] {text}\n"
        text_area.config(state=tk.NORMAL)
        text_area.insert(tk.END, formatted_text)
        text_area.config(state=tk.DISABLED)
        text_area.see(tk.END)
        self.app.queue_ui_message("status", "", f"✅ Распознано: {text[:30]}...", fg="green")
    def queue_message(self, msg_type, title="", message="", **kwargs):
        self.app.ui_queue.put((msg_type, title, message, kwargs))