import tkinter as tk
from tkinter import filedialog
from tkinter import ttk as ttk
class EventHandlers:
    def __init__(self, app):
        self.app = app
    def setup_bindings(self):
        root = self.app.root
        root.bind('<F7>', lambda e: self.handle_start_recording())
        root.bind('<F9>', lambda e: self.handle_stop_recording())
        root.bind('<Key>', self.universal_key_handler, add=True)
    def universal_key_handler(self, event):
        if event.state & 0x4:
            keycode = event.keycode
            c_keycodes = [67, 99, 1089, 1057]
            a_keycodes = [65, 97, 1092, 1060, 1040, 1072]
            if keycode in c_keycodes:
                self.app.copy_selected_text_universal()
                return "break"
            elif keycode in a_keycodes:
                self.app.select_all_text_universal()
                return "break"
    def handle_model_selection(self):
        model_manager = self.app.model_manager
        if not model_manager.is_vosk_available():
            self.app.queue_ui_message("error", "Ошибка", 
                                    "Библиотека Vosk не загружена!\nУстановите: pip install vosk")
            return
        path = filedialog.askdirectory(title="Выберите папку с моделью Vosk")
        if path:
            self.app.queue_ui_message("log", "", f"Выбран путь к модели: {path}")
            is_valid, message = model_manager.validate_model_path(path)
            if is_valid:
                model_manager.model_path = path
                self._show_loading_and_load_model()
            else:
                error_msg = f"Некорректная модель: {message}"
                self.app.queue_ui_message("log", "", f"❌ {error_msg}")
                self.app.queue_ui_message("error", "Ошибка", error_msg)
                self.app.queue_ui_message("status", "", "❌ Некорректная модель", fg="red")
    def _show_loading_and_load_model(self):
        loading_window = tk.Toplevel(self.app.root)
        loading_window.title("Загрузка модели")
        loading_window.geometry("400x150")
        loading_window.resizable(False, False)
        loading_window.transient(self.app.root)
        loading_window.geometry("+%d+%d" % (
            self.app.root.winfo_rootx() + 50,
            self.app.root.winfo_rooty() + 50))
        label = tk.Label(loading_window, text="Загрузка модели...\nЭто может занять несколько секунд", 
                       font=("Arial", 11), wraplength=350)
        label.pack(pady=20)
        progress = ttk.Progressbar(loading_window, mode='indeterminate')
        progress.pack(pady=10, padx=20, fill=tk.X)
        progress.start(10)
        
        loading_window.update()
        self.app.executor.submit(self._load_model_worker, loading_window)
    
    def _load_model_worker(self, loading_window):
        try:
            self.app.queue_ui_message("log", "", "Начало загрузки модели...")
            success = self.app.model_manager.load_model()
            if not success:
                raise Exception("Модель не создана")
            self.app.root.after(0, lambda: self._on_model_loaded(loading_window))
        except Exception as e:
            error_msg = str(e)
            self.app.root.after(0, lambda: self._on_model_load_error(loading_window, error_msg))
    
    def _on_model_loaded(self, loading_window):
        try:
            loading_window.destroy()
            model_name = self.app.model_manager.get_model_name()
            
            self.app.queue_ui_message("status", "", "✅ Модель загружена", fg="green")
            self.app.queue_ui_message("model_info", "", f"Модель: {model_name}")
            self.app.queue_ui_message("log", "", "✅ Модель успешно загружена")
            self.app.queue_ui_message("info", "Успех", 
                                    f"Модель загружена!\nПуть: {self.app.model_manager.model_path}")
        except Exception as e:
            self.app.queue_ui_message("log", "", f"❌ Ошибка при завершении загрузки: {e}")
    def _on_model_load_error(self, loading_window, error_msg):
        try:
            loading_window.destroy()
            self.app.queue_ui_message("log", "", f"❌ Ошибка загрузки модели: {error_msg}")
            self.app.queue_ui_message("error", "Ошибка", f"Ошибка загрузки модели:\n{error_msg}")
            self.app.queue_ui_message("status", "", "❌ Ошибка загрузки модели", fg="red")
            self.app.model_manager.model = None
        except Exception as e:
            self.app.queue_ui_message("log", "", f"❌ Ошибка обработки ошибки: {e}")
    def handle_start_recording(self):
        if not self.app.model_manager.is_model_loaded():
            self.app.queue_ui_message("error", "Ошибка", 
                                    "Модель не загружена!\nСначала выберите модель")
            return
        if not self.app.is_recording:
            self.app.is_recording = True
            self.app.recording_manager.reset_state()
            self.app.stop_flags['recording'].clear()
            self.app.stop_flags['processing'].clear()
            self.app.queue_ui_message("status", "", 
                                    "🎤 Запись активна... Говорите! (F9 для остановки)", fg="red")
            self.app.queue_ui_message("log", "", "=== Начало записи (F9 для остановки) ===")
            self.app.queue_ui_message("enable_buttons", "", "", 
                                    start=tk.DISABLED, stop=tk.NORMAL)
            self.app.recording_thread = self.app.executor.submit(self._record_audio_worker)
            self.app.processing_thread = self.app.executor.submit(self._process_audio_worker)
    def handle_stop_recording(self):
        if self.app.is_recording:
            self.app.is_recording = False
            self.app.stop_flags['recording'].set()
            self.app.stop_flags['processing'].set()
            self.app.queue_ui_message("status", "", "⏹ Запись остановлена", fg="black")
            self.app.queue_ui_message("log", "", "=== Запись остановлена ===")
            self.app.queue_ui_message("enable_buttons", "", "", 
                                    start=tk.NORMAL, stop=tk.DISABLED)
    def handle_clear_text(self):
        self.app.ui_elements['text_area'].delete(1.0, tk.END)
        self.app.queue_ui_message("status", "", "Текст очищен")
    def handle_clear_logs(self):
        self.app.ui_elements['log_area'].delete(1.0, tk.END)
        self.app.queue_ui_message("status", "", "Логи очищены")
    def _record_audio_worker(self):
        return self.app.recording_manager.record_audio(
            self.app.audio_queue,
            self.app.stop_flags['recording'],
            self.app.queue_ui_message
        )
    def _process_audio_worker(self):
        return self.app.recording_manager.process_audio(
            self.app.audio_queue,
            self.app.stop_flags['processing'],
            self.app.queue_ui_message
        )