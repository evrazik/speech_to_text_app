import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import threading
import queue
import pyaudio
import json
import os
from concurrent.futures import ThreadPoolExecutor
import time

class SpeechToTextApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Распознавание речи в реальном времени")
        self.root.geometry("850x750")
        self.root.resizable(True, True)
        
        # Пулы потоков для разных задач
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.audio_queue = queue.Queue(maxsize=10)  # Ограниченная очередь
        self.ui_queue = queue.Queue()
        
        self.model_path = None
        self.Model = None
        self.KaldiRecognizer = None
        self.model = None
        self.recognizer = None
        
        # Для предотвращения дублирования частичных результатов
        self.last_partial_text = ""
        self.partial_text_counter = 0
        self.max_partial_duplicates = 3
        
        # Инициализация Vosk
        self.init_vosk()
        
        # Аудио параметры
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 8192
        
        # Состояние записи
        self.is_recording = False
        self.audio_stream = None
        self.pyaudio_instance = None
        self.recording_thread = None
        self.processing_thread = None
        
        # Флаги для корректного завершения
        self.stop_recording_flag = threading.Event()
        self.stop_processing_flag = threading.Event()
        
        self.setup_ui()
        self.setup_bindings()
        
        # Запуск обработчика UI сообщений
        self.process_ui_queue()
        
    def setup_bindings(self):
        """Настройка горячих клавиш"""
        self.root.bind('<F7>', lambda e: self.start_recording())
        self.root.bind('<F9>', lambda e: self.stop_recording())
        self.root.bind('<Control-c>', self.copy_selected_text)
        self.root.bind('<Control-a>', self.select_all_text)
        self.root.bind('<Key>', self.global_key_handler)
    
    def global_key_handler(self, event):
        pass
    
    def copy_selected_text(self, event=None):
        """Копирование выделенного текста"""
        try:
            focused_widget = self.root.focus_get()
            if hasattr(focused_widget, 'selection_get'):
                selected_text = focused_widget.selection_get()
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
        except tk.TclError:
            pass
    
    def select_all_text(self, event=None):
        """Выделение всего текста"""
        try:
            focused_widget = self.root.focus_get()
            if hasattr(focused_widget, 'tag_add'):
                focused_widget.tag_add(tk.SEL, "1.0", tk.END)
                focused_widget.mark_set(tk.INSERT, "1.0")
                focused_widget.see(tk.INSERT)
                return "break"
        except tk.TclError:
            pass
    
    def init_vosk(self):
        """Инициализация Vosk библиотеки"""
        try:
            from vosk import Model, KaldiRecognizer
            self.Model = Model
            self.KaldiRecognizer = KaldiRecognizer
            print("Vosk библиотека загружена успешно")
            return True
        except ImportError as e:
            print(f"Ошибка импорта Vosk: {e}")
            self.queue_ui_message("error", "Ошибка", "Библиотека Vosk не установлена!\nУстановите: pip install vosk")
            return False
        except Exception as e:
            print(f"Ошибка загрузки Vosk: {e}")
            self.queue_ui_message("error", "Ошибка", f"Ошибка загрузки Vosk: {e}")
            return False
    
    def validate_model_path(self, path):
        """Проверка правильности пути к модели"""
        if not path or not os.path.exists(path):
            return False, "Путь не существует"
        
        if not os.path.isdir(path):
            return False, "Указанный путь не является папкой"
        
        readme_exists = any(os.path.exists(os.path.join(path, readme)) 
                           for readme in ['README', 'README.md', 'readme'])
        
        required_dirs = ['am', 'conf', 'graph']
        dirs_exist = all(os.path.exists(os.path.join(path, dir_name)) 
                        for dir_name in required_dirs)
        
        if readme_exists and dirs_exist:
            return True, "Модель корректна"
        else:
            missing = []
            if not readme_exists:
                missing.append("README файл")
            for dir_name in required_dirs:
                if not os.path.exists(os.path.join(path, dir_name)):
                    missing.append(f"папка {dir_name}")
            return False, f"Отсутствуют: {', '.join(missing)}"
    
    def fix_encoding(self, text):
        """Исправление проблем с кодировкой"""
        if isinstance(text, bytes):
            for encoding in ['utf-8', 'cp1251', 'cp866', 'latin1']:
                try:
                    return text.decode(encoding)
                except:
                    continue
            return text.decode('utf-8', errors='ignore')
        elif isinstance(text, str):
            try:
                if 'Р' in text and 'С' in text:
                    try:
                        bytes_text = text.encode('latin1')
                        return bytes_text.decode('cp1251')
                    except:
                        pass
            except:
                pass
            return text
        return str(text)
    
    def setup_ui(self):
        # Создание элементов интерфейса
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
        
        # Кнопка очистки
        self.btn_clear = tk.Button(frame_top, text="🗑 Очистить текст", 
                                  command=self.clear_text, 
                                  bg="orange", fg="white", width=15,
                                  font=("Arial", 10, "bold"))
        self.btn_clear.pack(side=tk.LEFT, padx=5)
        
        # Кнопка очистки логов
        self.btn_clear_logs = tk.Button(frame_top, text="🗑 Очистить логи", 
                                       command=self.clear_logs, 
                                       bg="darkorange", fg="white", width=15,
                                       font=("Arial", 10, "bold"))
        self.btn_clear_logs.pack(side=tk.LEFT, padx=5)
        
        # Кнопка выбора модели
        self.btn_model = tk.Button(frame_top, text="📂 Выбрать модель", 
                                  command=self.select_model, 
                                  bg="blue", fg="white", width=15,
                                  font=("Arial", 10, "bold"))
        self.btn_model.pack(side=tk.LEFT, padx=5)
        
        # Кнопка диагностики
        self.btn_diagnose = tk.Button(frame_top, text="🔍 Диагностика", 
                                     command=self.run_diagnostics, 
                                     bg="purple", fg="white", width=15,
                                     font=("Arial", 10, "bold"))
        self.btn_diagnose.pack(side=tk.LEFT, padx=5)
        
        # Текстовое поле для вывода результата
        text_frame = tk.Frame(self.root)
        text_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        tk.Label(text_frame, text="Распознанный текст:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        
        self.text_area = scrolledtext.ScrolledText(text_frame, 
                                                  wrap=tk.WORD, 
                                                  width=95, 
                                                  height=20,
                                                  font=("Arial", 11))
        self.text_area.pack(fill=tk.BOTH, expand=True)
        
        # Настройка контекстного меню для текста
        self.setup_text_context_menu(self.text_area)
        
        # Панель логов
        log_frame = tk.Frame(self.root)
        log_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        tk.Label(log_frame, text="Логи:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, 
                                                 wrap=tk.WORD, 
                                                 width=95, 
                                                 height=8,
                                                 font=("Courier", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # Настройка контекстного меню для логов
        self.setup_text_context_menu(self.log_area)
        
        # Статусная строка
        self.status_label = tk.Label(self.root, text="Готов к работе", 
                                    relief=tk.SUNKEN, anchor=tk.W,
                                    font=("Arial", 9))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Информационная панель
        info_frame = tk.Frame(self.root)
        info_frame.pack(pady=5)
        
        self.model_info_label = tk.Label(info_frame, text="Модель: Не выбрана", 
                                        font=("Arial", 8), fg="gray")
        self.model_info_label.pack()
        
        # Панель подсказок
        hint_frame = tk.Frame(self.root)
        hint_frame.pack(pady=3)
        
        tk.Label(hint_frame, text="Подсказки: F7 - Начать запись | F9 - Остановить запись | Ctrl+C - Копировать | Ctrl+A - Выделить всё", 
                font=("Arial", 8), fg="blue").pack()
    
    def setup_text_context_menu(self, text_widget):
        """Настройка контекстного меню для текстовых виджетов"""
        context_menu = tk.Menu(text_widget, tearoff=0)
        context_menu.add_command(label="Копировать", command=lambda: self.copy_text_from_widget(text_widget))
        context_menu.add_command(label="Выделить всё", command=lambda: self.select_all_from_widget(text_widget))
        context_menu.add_separator()
        context_menu.add_command(label="Очистить", command=lambda: text_widget.delete(1.0, tk.END))
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        text_widget.bind("<Button-3>", show_context_menu)
        text_widget.bind("<Control-c>", lambda e: self.copy_text_from_widget(text_widget))
        text_widget.bind("<Control-a>", lambda e: self.select_all_from_widget(text_widget))
    
    def copy_text_from_widget(self, widget):
        """Копирование выделенного текста из виджета"""
        try:
            selected_text = widget.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except tk.TclError:
            pass
    
    def select_all_from_widget(self, widget):
        """Выделение всего текста в виджете"""
        widget.tag_add(tk.SEL, "1.0", tk.END)
        widget.mark_set(tk.INSERT, "1.0")
        widget.see(tk.INSERT)
        widget.focus_set()
    
    def queue_ui_message(self, msg_type, title="", message="", **kwargs):
        """Постановка сообщения в очередь для обработки в UI потоке"""
        self.ui_queue.put((msg_type, title, message, kwargs))
    
    def process_ui_queue(self):
        """Обработка очереди UI сообщений"""
        try:
            while True:
                msg_type, title, message, kwargs = self.ui_queue.get_nowait()
                self.handle_ui_message(msg_type, title, message, **kwargs)
        except queue.Empty:
            pass
        finally:
            # Планируем следующую обработку
            self.root.after(100, self.process_ui_queue)
    
    def handle_ui_message(self, msg_type, title, message, **kwargs):
        """Обработка UI сообщений"""
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
        """Добавление сообщения в лог"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_area.insert(tk.END, log_entry)
        self.log_area.see(tk.END)
        self.log_area.update_idletasks()
        print(log_entry.strip())
    
    def run_diagnostics(self):
        """Запуск диагностики системы с правильной кодировкой"""
        def diagnostics_worker():
            self.queue_ui_message("log", "", "=== Запуск диагностики ===")
            
            try:
                p = pyaudio.PyAudio()
                info = p.get_host_api_info_by_index(0)
                numdevices = info.get('deviceCount')
                
                self.queue_ui_message("log", "", f"Найдено аудиоустройств: {numdevices}")
                
                for i in range(0, numdevices):
                    try:
                        device_info = p.get_device_info_by_host_api_device_index(0, i)
                        if device_info.get('maxInputChannels') > 0:
                            device_name = device_info.get('name', 'Неизвестное устройство')
                            device_name = self.fix_encoding(device_name)
                            self.queue_ui_message("log", "", f"Входное устройство {i}: {device_name}")
                    except Exception as e:
                        self.queue_ui_message("log", "", f"Ошибка получения информации об устройстве {i}: {e}")
                
                p.terminate()
                self.queue_ui_message("log", "", "✅ Диагностика аудио завершена")
                
            except Exception as e:
                self.queue_ui_message("log", "", f"❌ Ошибка диагностики: {e}")
        
        # Запускаем в пуле потоков
        self.executor.submit(diagnostics_worker)
    
    def select_model(self):
        """Выбор модели через диалог с прогрессбаром"""
        if not self.Model or not self.KaldiRecognizer:
            self.queue_ui_message("error", "Ошибка", "Библиотека Vosk не загружена!\nУстановите: pip install vosk")
            return
            
        path = filedialog.askdirectory(title="Выберите папку с моделью Vosk")
        if path:
            self.queue_ui_message("log", "", f"Выбран путь к модели: {path}")
            is_valid, message = self.validate_model_path(path)
            
            if is_valid:
                self.model_path = path
                
                # Создаем окно загрузки в UI потоке
                self.root.after(0, self._show_loading_and_load_model)
            else:
                error_msg = f"Некорректная модель: {message}"
                self.queue_ui_message("log", "", f"❌ {error_msg}")
                self.queue_ui_message("error", "Ошибка", error_msg)
                self.queue_ui_message("status", "", "❌ Некорректная модель", fg="red")
    
    def _show_loading_and_load_model(self):
        """Показ окна загрузки и запуск загрузки модели"""
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
        
        # Запускаем загрузку в отдельном потоке
        self.executor.submit(self._load_model_worker, loading_window)
    
    def _load_model_worker(self, loading_window):
        """Рабочая функция загрузки модели"""
        try:
            self.queue_ui_message("log", "", "Начало загрузки модели...")
            self.model = self.Model(self.model_path)
            
            if self.model is None:
                raise Exception("Модель не создана")
            
            # Успешная загрузка
            self.root.after(0, lambda: self._on_model_loaded(loading_window))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self._on_model_load_error(loading_window, error_msg))
    
    def _on_model_loaded(self, loading_window):
        """Обработка успешной загрузки модели"""
        try:
            loading_window.destroy()
            self.queue_ui_message("status", "", "✅ Модель загружена", fg="green")
            self.queue_ui_message("model_info", "", f"Модель: {os.path.basename(self.model_path)}")
            self.queue_ui_message("log", "", "✅ Модель успешно загружена")
            self.queue_ui_message("info", "Успех", f"Модель загружена!\nПуть: {self.model_path}")
        except Exception as e:
            self.queue_ui_message("log", "", f"❌ Ошибка при завершении загрузки: {e}")
    
    def _on_model_load_error(self, loading_window, error_msg):
        """Обработка ошибки загрузки модели"""
        try:
            loading_window.destroy()
            self.queue_ui_message("log", "", f"❌ Ошибка загрузки модели: {error_msg}")
            self.queue_ui_message("error", "Ошибка", f"Ошибка загрузки модели:\n{error_msg}")
            self.queue_ui_message("status", "", "❌ Ошибка загрузки модели", fg="red")
            self.model = None
        except Exception as e:
            self.queue_ui_message("log", "", f"❌ Ошибка обработки ошибки: {e}")
    
    def start_recording(self):
        """Начало записи в отдельном потоке"""
        if not self.model:
            self.queue_ui_message("error", "Ошибка", "Модель не загружена!\nСначала выберите модель")
            return
            
        if not self.is_recording:
            self.is_recording = True
            self.last_partial_text = ""
            self.partial_text_counter = 0
            self.stop_recording_flag.clear()
            self.stop_processing_flag.clear()
            
            self.queue_ui_message("status", "", "🎤 Запись активна... Говорите! (F9 для остановки)", fg="red")
            self.queue_ui_message("log", "", "=== Начало записи (F9 для остановки) ===")
            self.queue_ui_message("enable_buttons", "", "", start=tk.DISABLED, stop=tk.NORMAL)
            
            # Запуск потоков записи и обработки
            self.recording_thread = threading.Thread(target=self._record_audio_worker, daemon=True)
            self.processing_thread = threading.Thread(target=self._process_audio_worker, daemon=True)
            
            self.recording_thread.start()
            self.processing_thread.start()
    
    def stop_recording(self):
        """Остановка записи"""
        if self.is_recording:
            self.is_recording = False
            self.stop_recording_flag.set()
            self.stop_processing_flag.set()
            
            self.queue_ui_message("status", "", "⏹ Запись остановлена", fg="black")
            self.queue_ui_message("log", "", "=== Запись остановлена ===")
            self.queue_ui_message("enable_buttons", "", "", start=tk.NORMAL, stop=tk.DISABLED)
    
    def _record_audio_worker(self):
        """Рабочий поток для записи аудио"""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.queue_ui_message("log", "", f"Создание распознавателя с частотой {self.rate}Hz")
            
            # Создаем распознаватель
            self.recognizer = self.KaldiRecognizer(self.model, self.rate)
            if self.recognizer is None:
                raise Exception("Распознаватель не создан")
            
            self.queue_ui_message("log", "", "Распознаватель создан успешно")
            
            # Открытие аудиопотока
            self.queue_ui_message("log", "", "Открытие аудиопотока...")
            self.audio_stream = self.pyaudio_instance.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            self.audio_stream.start_stream()
            self.queue_ui_message("log", "", "Аудиопоток запущен")
            
            while not self.stop_recording_flag.is_set():
                try:
                    # Читаем аудиоданные с таймаутом
                    data = self.audio_stream.read(self.chunk, exception_on_overflow=False)
                    
                    if len(data) > 0:
                        # Помещаем данные в очередь (неблокирующая операция)
                        try:
                            self.audio_queue.put_nowait(data)
                        except queue.Full:
                            # Если очередь полна, пропускаем данные
                            self.queue_ui_message("log", "", "Очередь аудио переполнена, данные пропущены")
                            
                except Exception as e:
                    if not self.stop_recording_flag.is_set():
                        self.queue_ui_message("log", "", f"Ошибка чтения аудио: {e}")
                    break
                    
        except Exception as e:
            self.queue_ui_message("log", "", f"❌ Ошибка записи: {e}")
        finally:
            # Очистка ресурсов
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()
            self.queue_ui_message("log", "", "Аудиопоток закрыт")
    
    def _process_audio_worker(self):
        """Рабочий поток для обработки аудио данных"""
        while not self.stop_processing_flag.is_set():
            try:
                # Получаем аудиоданные из очереди с таймаутом
                data = self.audio_queue.get(timeout=0.1)
                
                if self.recognizer and data:
                    # Отправляем данные на распознавание
                    result_accepted = self.recognizer.AcceptWaveform(data)
                    
                    if result_accepted:
                        # Получаем полный результат
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            self.queue_ui_message("log", "", f"РАСПОЗНАНО: '{text}'")
                            self.queue_ui_message("text", "", text)
                            # Сброс счетчиков при полном результате
                            self.last_partial_text = ""
                            self.partial_text_counter = 0
                        else:
                            self.queue_ui_message("log", "", "Получен пустой результат")
                    else:
                        # Частичный результат
                        partial_result = json.loads(self.recognizer.PartialResult())
                        partial_text = partial_result.get("partial", "").strip()
                        
                        if partial_text:
                            # Проверяем, не повторяется ли текст
                            if partial_text == self.last_partial_text:
                                self.partial_text_counter += 1
                                if self.partial_text_counter <= self.max_partial_duplicates:
                                    self.queue_ui_message("log", "", f"ЧАСТИЧНО: '{partial_text}' (повтор {self.partial_text_counter})")
                            else:
                                self.last_partial_text = partial_text
                                self.partial_text_counter = 1
                                self.queue_ui_message("log", "", f"ЧАСТИЧНО: '{partial_text}'")
                        elif self.last_partial_text:
                            self.last_partial_text = ""
                            self.partial_text_counter = 0
                            
            except queue.Empty:
                # Таймаут очереди - продолжаем цикл
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
        timestamp = self.get_timestamp()
        formatted_text = f"[{timestamp}] {text}"
        self.text_area.insert(tk.END, formatted_text + "\n")
        self.text_area.see(tk.END)
        self.queue_ui_message("status", "", f"✅ Распознано: {text[:30]}...", fg="green")
    
    def get_timestamp(self):
        import datetime
        return datetime.datetime.now().strftime("%H:%M:%S")
    
    def cleanup(self):
        """Очистка ресурсов при закрытии приложения"""
        self.stop_recording()
        self.executor.shutdown(wait=False)
    
    def __del__(self):
        """Деструктор для очистки ресурсов"""
        self.cleanup()

def main():
    root = tk.Tk()
    
    def on_closing():
        # Очистка перед закрытием
        app.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    app = SpeechToTextApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
