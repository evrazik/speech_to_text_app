import pyaudio
import json
class AudioProcessor:
    def __init__(self):
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 8192
        self.audio_stream = None
        self.pyaudio_instance = None
        self.recognizer = None
        self.last_partial_text = ""
        self.partial_text_counter = 0
        self.max_partial_duplicates = 3
    def create_recognizer(self, model):
        try:
            from vosk import KaldiRecognizer
            self.recognizer = KaldiRecognizer(model, self.rate)
            return self.recognizer is not None
        except Exception as e:
            print(f"Ошибка создания распознавателя: {e}")
            return False
    def open_audio_stream(self):
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.audio_stream = self.pyaudio_instance.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            self.audio_stream.start_stream()
            return True
        except Exception as e:
            print(f"Ошибка открытия аудиопотока: {e}")
            return False
    def read_audio_chunk(self, max_queue_size):
        try:
            if self.audio_stream:
                return self.audio_stream.read(self.chunk, exception_on_overflow=False)
            return None
        except Exception as e:
            print(f"Ошибка чтения аудио: {e}")
            return None
    def process_audio_chunk(self, data):
        if self.recognizer and data:
            return self.recognizer.AcceptWaveform(data)
        return False
    def get_full_result(self):
        try:
            if self.recognizer:
                result = json.loads(self.recognizer.Result())
                return result.get("text", "").strip()
        except Exception as e:
            print(f"Ошибка получения результата: {e}")
        return ""
    def get_partial_result(self):
        try:
            if self.recognizer:
                partial_result = json.loads(self.recognizer.PartialResult())
                return partial_result.get("partial", "").strip()
        except Exception as e:
            print(f"Ошибка получения частичного результата: {e}")
        return ""
    def should_log_partial(self, partial_text):
        if partial_text == self.last_partial_text:
            self.partial_text_counter += 1
            if self.partial_text_counter <= self.max_partial_duplicates:
                return True, f"ЧАСТИЧНО: '{partial_text}' (повтор {self.partial_text_counter})"
        else:
            self.last_partial_text = partial_text
            self.partial_text_counter = 1
            return True, f"ЧАСТИЧНО: '{partial_text}'"
        return False, ""
    def has_partial_text(self):
        return bool(self.last_partial_text)
    def clear_partial_state(self):
        self.last_partial_text = ""
        self.partial_text_counter = 0
    def reset_partial_text_state(self):
        self.last_partial_text = ""
        self.partial_text_counter = 0
    def cleanup(self):
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except:
                pass
            finally:
                self.audio_stream = None
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except:
                pass
            finally:
                self.pyaudio_instance = None
        self.recognizer = None
