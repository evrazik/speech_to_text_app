import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import threading
import queue
from concurrent.futures import ThreadPoolExecutor

from ui_components import UIComponents
from model_manager import ModelManager
from audio_processor import AudioProcessor
from utils import Utils

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
        self.audio_processor = AudioProcessor()
        self.ui_components = UIComponents()
        self.utils = Utils()
        self.is_recording = False
        self.recording_thread = None
        self.processing_thread = None
        self.stop_recording_flag = threading.Event()
        self.stop_processing_flag = threading.Event()
        self.setup_ui()
        self.setup_bindings()
        self.process_ui_queue()
    def setup_bindings(self):
        self.ui_components.setup_global_bindings(self.root, self)
    def setup_ui(self):
        frame_top = tk.Frame(self.root)
        frame_top.pack(pady=10)
        self.btn_start = tk.Button(frame_top, text="🔴 Начать запись (F7)", 
                                  command=self.start_recording, 
                                  bg="green", fg="white", width=20,
                                  font=("Arial", 10, "bold"))
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = tk.Button(frame_top, text="⏹ Остановить запись (F9)", 
                                 command=self.stop_recording, 
                                 bg="red", fg="white", width=20,
                                 state=tk.DISABLED,
                                 font=("Arial", 10, "bold"))
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        self.btn_clear = tk.Button(frame_top, text="🗑 Очистить текст", 
                                  command=self.clear_text, 
                                  bg="orange", fg="white", width=15,
                                  font=("Arial", 10, "bold"))
        self.btn_clear.pack(side=tk.LEFT, padx=5)
        
        self.btn_clear_logs = tk.Button(frame_top, text="🗑 Очистить логи", 
                                       command=self.clear_logs, 
                                       bg="darkorange", fg="white", width=15,
                                       font=("Arial", 10, "bold"))
        self.btn_clear_logs.pack(side=tk.LEFT, padx=5)
        
        self.btn_model = tk.Button(frame_top, text="📂 Выбрать модель", 
                                  command=self.select_model, 
                                  bg="blue", fg="white", width=15,
                                  font=("Arial", 10, "bold"))
        self.btn_model.pack(side=tk.LEFT, padx=5)
        text_frame = tk.Frame(self.root)
        text_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        tk.Label(text_frame, text="Распознанный текст:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        self.text_area = scrolledtext.ScrolledText(text_frame, 
                                                  wrap=tk.WORD, 
                                                  width=95, 
                                                  height=20,
                                                  font=("Arial", 11))
        self.text_area.pack(fill=tk.BOTH, expand=True)
        self.ui_components.setup_text_widget_bindings(self.text_area, self)
        log_frame = tk.Frame(self.root)
        log_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        tk.Label(log_frame, text="Логи:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        self.log_area = scrolledtext.ScrolledText(log_frame, 
                                                 wrap=tk.WORD, 
                                                 width=95, 
                                                 height=8,
                                                 font=("Courier", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.ui_components.setup_text_widget_bindings(self.log_area, self)
        self.status_label = tk.Label(self.root, text="Готов к работе", 
                                    relief=tk.SUNKEN, anchor=tk.W,
                                    font=("Arial", 9))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        info_frame = tk.Frame(self.root)
        info_frame.pack(pady=5)
        
        self.model_info_label = tk.Label(info_frame, text="Модель: Не выбрана", 
                                        font=("Arial", 8), fg="gray")
        self.model_info_label.pack()
        hint_frame = tk.Frame(self.root)
        hint_frame.pack(pady=3)
        tk.Label(hint_frame, text="Подсказки: F7 - Начать запись | F9 - Остановить запись | Ctrl+C - Копировать | Ctrl+A - Выделить всё", 
                font=("Arial", 8), fg="blue").pack()
    def process_ui_queue(self):
        try:
            while True:
                msg_type, title, message, kwargs = self.ui_queue.get_nowait()
                self.handle_ui_message(msg_type, title, message, **kwargs)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_ui_queue)
    def handle_ui_message(self, msg_type, title, message, **kwargs):
        if msg_type == "log":
            self.log_message(message)
        elif msg_type == "status":
            self.status_label.config(text=message, **kwargs)
        elif msg_type == "text":
            self.update_text(message)
        elif msg_type == "model_info":
            self.model_info_label.config(text=message)
        elif msg_type == "error":
            messagebox.showerror(title, message)
        elif msg_type == "info":
            messagebox.showinfo(title, message)
        elif msg_type == "enable_buttons":
            self.btn_start.config(state=kwargs.get('start', tk.NORMAL))
            self.btn_stop.config(state=kwargs.get('stop', tk.NORMAL))
    def log_message(self, message):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_area.insert(tk.END, log_entry)
        self.log_area.see(tk.END)
        self.log_area.update_idletasks()
        print(log_entry.strip())
    
    def select_model(self):
        if not self.model_manager.is_vosk_available():
            self.queue_ui_message("error", "Ошибка", "Библиотека Vosk не загружена!\nУстановите: pip install vosk")
            return
        path = filedialog.askdirectory(title="Выберите папку с моделью Vosk")
        if path:
            self.queue_ui_message("log", "", f"Выбран путь к модели: {path}")
            is_valid, message = self.model_manager.validate_model_path(path)
            if is_valid:
                self.model_manager.model_path = path
                self.root.after(0, self._show_loading_and_load_model)
            else:
                error_msg = f"Некорректная модель: {message}"
                self.queue_ui_message("log", "", f"❌ {error_msg}")
                self.queue_ui_message("error", "Ошибка", error_msg)
                self.queue_ui_message("status", "", "❌ Некорректная модель", fg="red")
    def _show_loading_and_load_model(self):
        loading_window = tk.Toplevel(self.root)
        loading_window.title("Загрузка модели")
        loading_window.geometry("400x150")
        loading_window.resizable(False, False)
        loading_window.transient(self.root)
        loading_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50))
        label = tk.Label(loading_window, text="Загрузка модели...\nЭто может занять несколько секунд", 
                       font=("Arial", 11), wraplength=350)
        label.pack(pady=20)
        import tkinter.ttk as ttk
        progress = ttk.Progressbar(loading_window, mode='indeterminate')
        progress.pack(pady=10, padx=20, fill=tk.X)
        progress.start(10)
        
        loading_window.update()
        self.executor.submit(self._load_model_worker, loading_window)
    def _load_model_worker(self, loading_window):
        try:
            self.queue_ui_message("log", "", "Начало загрузки модели...")
            success = self.model_manager.load_model()
            if not success:
                raise Exception("Модель не создана")
            self.root.after(0, lambda: self._on_model_loaded(loading_window))
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self._on_model_load_error(loading_window, error_msg))
    def _on_model_loaded(self, loading_window):
        try:
            loading_window.destroy()
            self.queue_ui_message("status", "", "✅ Модель загружена", fg="green")
            self.queue_ui_message("model_info", "", f"Модель: {self.model_manager.get_model_name()}")
            self.queue_ui_message("log", "", "✅ Модель успешно загружена")
            self.queue_ui_message("info", "Успех", f"Модель загружена!\nПуть: {self.model_manager.model_path}")
        except Exception as e:
            self.queue_ui_message("log", "", f"❌ Ошибка при завершении загрузки: {e}")
    def _on_model_load_error(self, loading_window, error_msg):
        try:
            loading_window.destroy()
            self.queue_ui_message("log", "", f"❌ Ошибка загрузки модели: {error_msg}")
            self.queue_ui_message("error", "Ошибка", f"Ошибка загрузки модели:\n{error_msg}")
            self.queue_ui_message("status", "", "❌ Ошибка загрузки модели", fg="red")
            self.model_manager.model = None
        except Exception as e:
            self.queue_ui_message("log", "", f"❌ Ошибка обработки ошибки: {e}")
    def start_recording(self):
        if not self.model_manager.is_model_loaded():
            self.queue_ui_message("error", "Ошибка", "Модель не загружена!\nСначала выберите модель")
            return
        if not self.is_recording:
            self.is_recording = True
            self.audio_processor.reset_partial_text_state()
            self.stop_recording_flag.clear()
            self.stop_processing_flag.clear()
            
            self.queue_ui_message("status", "", "🎤 Запись активна... Говорите! (F9 для остановки)", fg="red")
            self.queue_ui_message("log", "", "=== Начало записи (F9 для остановки) ===")
            self.queue_ui_message("enable_buttons", "", "", start=tk.DISABLED, stop=tk.NORMAL)
            
            self.recording_thread = threading.Thread(target=self._record_audio_worker, daemon=True)
            self.processing_thread = threading.Thread(target=self._process_audio_worker, daemon=True)
            
            self.recording_thread.start()
            self.processing_thread.start()
    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.stop_recording_flag.set()
            self.stop_processing_flag.set()
            
            self.queue_ui_message("status", "", "⏹ Запись остановлена", fg="black")
            self.queue_ui_message("log", "", "=== Запись остановлена ===")
            self.queue_ui_message("enable_buttons", "", "", start=tk.NORMAL, stop=tk.DISABLED)
    def _record_audio_worker(self):
        try:
            self.queue_ui_message("log", "", f"Создание распознавателя с частотой {self.audio_processor.rate}Hz")
            success = self.audio_processor.create_recognizer(self.model_manager.model)
            if not success:
                raise Exception("Распознаватель не создан")
            self.queue_ui_message("log", "", "Распознаватель создан успешно")
            self.queue_ui_message("log", "", "Открытие аудиопотока...")
            success = self.audio_processor.open_audio_stream()
            if not success:
                raise Exception("Не удалось открыть аудиопоток")
            self.queue_ui_message("log", "", "Аудиопоток запущен")
            while not self.stop_recording_flag.is_set():
                try:
                    data = self.audio_processor.read_audio_chunk(self.audio_queue.maxsize)
                    if data and len(data) > 0:
                        try:
                            self.audio_queue.put_nowait(data)
                        except queue.Full:
                            self.queue_ui_message("log", "", "Очередь аудио переполнена, данные пропущены")
                except Exception as e:
                    if not self.stop_recording_flag.is_set():
                        self.queue_ui_message("log", "", f"Ошибка чтения аудио: {e}")
                    break
        except Exception as e:
            self.queue_ui_message("log", "", f"❌ Ошибка записи: {e}")
        finally:
            self.audio_processor.cleanup()
            self.queue_ui_message("log", "", "Аудиопоток закрыт")
    def _process_audio_worker(self):
        while not self.stop_processing_flag.is_set():
            try:
                data = self.audio_queue.get(timeout=0.1)
                if self.audio_processor.recognizer and data:
                    result_accepted = self.audio_processor.process_audio_chunk(data)
                    if result_accepted:
                        text = self.audio_processor.get_full_result()
                        if text:
                            self.queue_ui_message("log", "", f"РАСПОЗНАНО: '{text}'")
                            self.queue_ui_message("text", "", text)
                            self.audio_processor.reset_partial_text_state()
                        else:
                            self.queue_ui_message("log", "", "Получен пустой результат")
                    else:
                        partial_text = self.audio_processor.get_partial_result()
                        if partial_text:
                            should_log, log_message = self.audio_processor.should_log_partial(partial_text)
                            if should_log:
                                self.queue_ui_message("log", "", log_message)
                        elif self.audio_processor.has_partial_text():
                            self.audio_processor.clear_partial_state()
            except queue.Empty:
                continue
            except Exception as e:
                if not self.stop_processing_flag.is_set():
                    self.queue_ui_message("log", "", f"❌ Ошибка обработки аудио: {e}")
                break
    def clear_text(self):
        self.text_area.delete(1.0, tk.END)
        self.queue_ui_message("status", "", "Текст очищен")
    def clear_logs(self):
        self.log_area.delete(1.0, tk.END)
        self.queue_ui_message("status", "", "Логи очищены")
    def update_text(self, text):
        timestamp = self.utils.get_timestamp()
        formatted_text = f"[{timestamp}] {text}"
        self.text_area.insert(tk.END, formatted_text + "\n")
        self.text_area.see(tk.END)
        self.queue_ui_message("status", "", f"✅ Распознано: {text[:30]}...", fg="green")
    def queue_ui_message(self, msg_type, title="", message="", **kwargs):
        self.ui_queue.put((msg_type, title, message, kwargs))
    def cleanup(self):
        self.stop_recording()
        self.executor.shutdown(wait=False)
        self.audio_processor.cleanup()
    def __del__(self):
        self.cleanup()
