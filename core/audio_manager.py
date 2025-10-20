import pyaudio
class AudioManager:
    def __init__(self):
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 8192
        self.audio_stream = None
        self.pyaudio_instance = None
        self.recognizer = None
    def create_recognizer(self, model):
        try:
            if model is None:
                return False
            from vosk import KaldiRecognizer
            self.recognizer = KaldiRecognizer(model, self.rate)
            return self.recognizer is not None
        except Exception as e:
            print(f"Ошибка создания распознавателя: {e}")
            self.recognizer = None
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
            self.cleanup()
            return False
    def read_audio_chunk(self):
        try:
            if self.audio_stream and self.audio_stream.is_active():
                return self.audio_stream.read(self.chunk, exception_on_overflow=False)
            return None
        except Exception as e:
            print(f"Ошибка чтения аудио: {e}")
            return None
    def is_stream_active(self):
        return self.audio_stream is not None and self.audio_stream.is_active()
    def get_audio_devices_info(self):
        try:
            if self.pyaudio_instance is None:
                self.pyaudio_instance = pyaudio.PyAudio()
            info = self.pyaudio_instance.get_host_api_info_by_index(0)
            numdevices = info.get('deviceCount')
            devices = []
            for i in range(0, numdevices):
                device_info = self.pyaudio_instance.get_device_info_by_host_api_device_index(0, i)
                if device_info.get('maxInputChannels') > 0:
                    devices.append({
                        'index': i,
                        'name': device_info.get('name', 'Неизвестное устройство'),
                        'channels': device_info.get('maxInputChannels'),
                        'rate': device_info.get('defaultSampleRate')
                    })
            return devices
        except Exception as e:
            print(f"Ошибка получения информации об устройствах: {e}")
            return []
    def cleanup(self):
        if self.audio_stream:
            try:
                if self.audio_stream.is_active():
                    self.audio_stream.stop_stream()
                self.audio_stream.close()
            except Exception as e:
                print(f"Ошибка закрытия аудио потока: {e}")
            finally:
                self.audio_stream = None
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except Exception as e:
                print(f"Ошибка завершения PyAudio: {e}")
            finally:
                self.pyaudio_instance = None
        self.recognizer = None
    def __del__(self):
        self.cleanup()
    @property
    def sample_rate(self):
        return self.rate
    @property
    def chunk_size(self):
        return self.chunk
    @property
    def is_ready(self):
        return self.pyaudio_instance is not None and self.audio_stream is not None