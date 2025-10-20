import os
class ModelManager:
    def __init__(self):
        self.model_path = None
        self.model = None
        self.Model = None
        self.KaldiRecognizer = None
        self.init_vosk()
    def init_vosk(self):
        try:
            from vosk import Model, KaldiRecognizer
            self.Model = Model
            self.KaldiRecognizer = KaldiRecognizer
            print("Vosk библиотека загружена успешно")
            return True
        except ImportError as e:
            print(f"Ошибка импорта Vosk: {e}")
            return False
        except Exception as e:
            print(f"Ошибка загрузки Vosk: {e}")
            return False
    def is_vosk_available(self):
        return self.Model is not None and self.KaldiRecognizer is not None
    def validate_model_path(self, path):
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
    def load_model(self):
        if not self.is_vosk_available() or not self.model_path:
            return False
        
        try:
            self.model = self.Model(self.model_path)
            return self.model is not None
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            self.model = None
            return False
    def is_model_loaded(self):
        return self.model is not None
    def get_model_name(self):
        if self.model_path:
            return os.path.basename(self.model_path)
        return "Не выбрана"