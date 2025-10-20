import tkinter as tk
class UIComponents:
    def setup_global_bindings(self, root, app):
        root.bind('<F7>', lambda e: app.start_recording())
        root.bind('<F9>', lambda e: app.stop_recording())
        root.bind('<Key>', lambda e: self.universal_key_handler(e, app), add=True)
    def universal_key_handler(self, event, app):
        if event.state & 0x4:
            keycode = event.keycode
            c_keycodes = [67, 99, 1089, 1057]
            a_keycodes = [65, 97, 1092, 1060, 1040, 1072]
            
            if keycode in c_keycodes:
                app.copy_selected_text_universal()
                return "break"
            elif keycode in a_keycodes:
                app.select_all_text_universal()
                return "break"
    def setup_text_widget_bindings(self, text_widget, app):
        context_menu = tk.Menu(text_widget, tearoff=0)
        context_menu.add_command(label="Копировать", command=lambda: app.copy_text_from_widget(text_widget))
        context_menu.add_command(label="Выделить всё", command=lambda: app.select_all_from_widget(text_widget))
        context_menu.add_separator()
        context_menu.add_command(label="Очистить", command=lambda: text_widget.delete(1.0, tk.END))
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
            if event.state & 0x4:  # Ctrl нажат
                if event.keysym.lower() in ['c', 'с']:
                    app.copy_text_from_widget(text_widget)
                    return "break"
                elif event.keysym.lower() in ['a', 'ф']:
                    app.select_all_from_widget(text_widget)
                    return "break"
        text_widget.bind("<KeyPress>", key_press_handler)
