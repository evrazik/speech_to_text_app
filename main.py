import tkinter as tk
from app import SpeechToTextApp
def main():
    root = tk.Tk()
    def on_closing():
        try:
            app = root.app_instance  # Если сохраняли ссылку
            if hasattr(app, 'cleanup'):
                app.cleanup()
        except:
            pass
        finally:
            root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    app = SpeechToTextApp(root)
    root.app_instance = app
    root.mainloop()
if __name__ == "__main__":
    main()