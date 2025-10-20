import tkinter as tk
from tkinter import scrolledtext as st
class UISetup:
    def create_interface(self, root, app):
        ui_elements = {}
        ui_elements.update(self._create_top_panel(root, app))
        ui_elements.update(self._create_text_area(root, app))
        ui_elements.update(self._create_log_area(root, app))
        ui_elements.update(self._create_status_bar(root, app))
        return ui_elements
    def _create_top_panel(self, root, app):
        frame_top = tk.Frame(root)
        frame_top.pack(pady=10)
        buttons = {}
        buttons['btn_start'] = tk.Button(frame_top, text="🔴 Начать запись (F7)", 
                                       command=app.start_recording, 
                                       bg="green", fg="white", width=20,
                                       font=("Arial", 10, "bold"))
        buttons['btn_start'].pack(side=tk.LEFT, padx=5)
        buttons['btn_stop'] = tk.Button(frame_top, text="⏹ Остановить запись (F9)", 
                                      command=app.stop_recording, 
                                      bg="red", fg="white", width=24,
                                      state=tk.DISABLED,
                                      font=("Arial", 10, "bold"))
        buttons['btn_stop'].pack(side=tk.LEFT, padx=5)
        buttons['btn_clear'] = tk.Button(frame_top, text="🗑 Очистить текст", 
                                       command=app.clear_text, 
                                       bg="orange", fg="white", width=15,
                                       font=("Arial", 10, "bold"))
        buttons['btn_clear'].pack(side=tk.LEFT, padx=5)
        buttons['btn_clear_logs'] = tk.Button(frame_top, text="🗑 Очистить логи", 
                                            command=app.clear_logs, 
                                            bg="darkorange", fg="white", width=15,
                                            font=("Arial", 10, "bold"))
        buttons['btn_clear_logs'].pack(side=tk.LEFT, padx=5)
        buttons['btn_model'] = tk.Button(frame_top, text="📂 Выбрать модель", 
                                       command=app.select_model, 
                                       bg="blue", fg="white", width=18,
                                       font=("Arial", 10, "bold"))
        buttons['btn_model'].pack(side=tk.LEFT, padx=5)
        return buttons
    def _create_text_area(self, root, app):
        text_frame = tk.Frame(root)
        text_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        tk.Label(text_frame, text="Распознанный текст:", 
                font=("Arial", 9, "bold")).pack(anchor=tk.W)
        text_area = st.ScrolledText(text_frame, 
                                            wrap=tk.WORD, 
                                            width=95, 
                                            height=20,
                                            font=("Arial", 11))
        text_area.pack(fill=tk.BOTH, expand=True)
        self._setup_context_menu(text_area, app)
        return {'text_area': text_area}
    def _create_log_area(self, root, app):
        log_frame = tk.Frame(root)
        log_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        tk.Label(log_frame, text="Логи:", 
                font=("Arial", 9, "bold")).pack(anchor=tk.W)
        log_area = st.ScrolledText(log_frame, 
                                           wrap=tk.WORD, 
                                           width=95, 
                                           height=8,
                                           font=("Courier", 9))
        log_area.pack(fill=tk.BOTH, expand=True)
        self._setup_context_menu(log_area, app)
        return {'log_area': log_area}
    def _setup_context_menu(self, text_widget, app):
        context_menu = tk.Menu(text_widget, tearoff=0)
        context_menu.add_command(label="Копировать", 
                               command=lambda: app.copy_text_from_widget(text_widget))
        context_menu.add_command(label="Выделить всё", 
                               command=lambda: app.select_all_from_widget(text_widget))
        context_menu.add_separator()
        context_menu.add_command(label="Очистить", 
                               command=lambda: text_widget.delete(1.0, tk.END))
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        text_widget.bind("<Button-3>", show_context_menu)
        text_widget.bind("<Control-c>", lambda e: [app.copy_text_from_widget(text_widget), "break"][1])
        text_widget.bind("<Control-C>", lambda e: [app.copy_text_from_widget(text_widget), "break"][1])
        text_widget.bind("<Control-a>", lambda e: [app.select_all_from_widget(text_widget), "break"][1])
        text_widget.bind("<Control-A>", lambda e: [app.select_all_from_widget(text_widget), "break"][1])
        def key_press_handler(event):
            if event.state & 0x4:
                if event.keysym.lower() in ['c', 'с']:
                    app.copy_text_from_widget(text_widget)
                    return "break"
                elif event.keysym.lower() in ['a', 'ф']:
                    app.select_all_from_widget(text_widget)
                    return "break"
        text_widget.bind("<KeyPress>", key_press_handler)
    def _create_status_bar(self, root, app):
        status_label = tk.Label(root, text="Готов к работе", 
                              relief=tk.SUNKEN, anchor=tk.W,
                              font=("Arial", 9))
        status_label.pack(side=tk.BOTTOM, fill=tk.X)
        info_frame = tk.Frame(root)
        info_frame.pack(pady=5)
        model_info_label = tk.Label(info_frame, text="Модель: Не выбрана", 
                                  font=("Arial", 8), fg="gray")
        model_info_label.pack()
        hint_frame = tk.Frame(root)
        hint_frame.pack(pady=3)
        tk.Label(hint_frame, 
                text="Подсказки: F7 - Начать запись | F9 - Остановить запись | Ctrl+C - Копировать | Ctrl+A - Выделить всё", 
                font=("Arial", 8), fg="blue").pack()
        return {
            'status_label': status_label,
            'model_info_label': model_info_label
        }