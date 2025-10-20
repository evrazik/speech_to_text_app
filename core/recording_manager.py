import json
import queue
class RecordingManager:
    def __init__(self, audio_manager, model_manager):
        self.audio_manager = audio_manager
        self.model_manager = model_manager
        self.last_partial_text = ""
        self.partial_text_counter = 0
        self.max_partial_duplicates = 3
    def reset_state(self):
        self.last_partial_text = ""
        self.partial_text_counter = 0
    def record_audio(self, audio_queue, stop_flag, message_queue_func):
        try:
            message_queue_func("log", "", f"Создание распознавателя с частотой {self.audio_manager.rate}Hz")
            success = self.audio_manager.create_recognizer(self.model_manager.model)
            if not success:
                raise Exception("Распознаватель не создан")
            message_queue_func("log", "", "Распознаватель создан успешно")
            message_queue_func("log", "", "Открытие аудиопотока...")
            success = self.audio_manager.open_audio_stream()
            if not success:
                raise Exception("Не удалось открыть аудиопоток")
            message_queue_func("log", "", "Аудиопоток запущен")
            while not stop_flag.is_set():
                try:
                    data = self.audio_manager.read_audio_chunk()
                    if data and len(data) > 0:
                        try:
                            audio_queue.put_nowait(data)
                        except queue.Full:
                            message_queue_func("log", "", "Очередь аудио переполнена, данные пропущены")
                except Exception as e:
                    if not stop_flag.is_set():
                        message_queue_func("log", "", f"Ошибка чтения аудио: {e}")
                    break
        except Exception as e:
            message_queue_func("log", "", f"❌ Ошибка записи: {e}")
        finally:
            self.audio_manager.cleanup()
            message_queue_func("log", "", "Аудиопоток закрыт")
    def process_audio(self, audio_queue, stop_flag, message_queue_func):
        while not stop_flag.is_set():
            try:
                data = audio_queue.get(timeout=0.1)
                if self.audio_manager.recognizer and data:
                    result_accepted = self.audio_manager.recognizer.AcceptWaveform(data)
                    if result_accepted:
                        result = json.loads(self.audio_manager.recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            message_queue_func("log", "", f"РАСПОЗНАНО: '{text}'")
                            message_queue_func("text", "", text)
                            self.reset_state()
                        else:
                            message_queue_func("log", "", "Получен пустой результат")
                    else:
                        partial_result = json.loads(self.audio_manager.recognizer.PartialResult())
                        partial_text = partial_result.get("partial", "").strip()
                        
                        if partial_text:
                            should_log, log_message = self._should_log_partial(partial_text)
                            if should_log:
                                message_queue_func("log", "", log_message)
                        elif self.last_partial_text:
                            self.reset_state()
            except queue.Empty:
                continue
            except Exception as e:
                if not stop_flag.is_set():
                    message_queue_func("log", "", f"❌ Ошибка обработки аудио: {e}")
                break
    def _should_log_partial(self, partial_text):
        if partial_text == self.last_partial_text:
            self.partial_text_counter += 1
            if self.partial_text_counter <= self.max_partial_duplicates:
                return True, f"ЧАСТИЧНО: '{partial_text}' (повтор {self.partial_text_counter})"
        else:
            self.last_partial_text = partial_text
            self.partial_text_counter = 1
            return True, f"ЧАСТИЧНО: '{partial_text}'"
        return False, ""