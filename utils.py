import datetime
class Utils:
    def get_timestamp(self):
        return datetime.datetime.now().strftime("%H:%M:%S")
    def fix_encoding(self, text):
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