import datetime
class Utils:
    @staticmethod
    def get_timestamp():
        return datetime.datetime.now().strftime("%H:%M:%S")
    @staticmethod
    def fix_encoding(text):
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
    @staticmethod
    def format_time_delta(seconds):
        if seconds < 60:
            return f"{seconds:.1f} сек"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} мин"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} ч"
    @staticmethod
    def truncate_text(text, max_length=100):
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."