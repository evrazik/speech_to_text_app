"""
Ядро приложения - основные функциональные компоненты
"""

from .audio_manager import AudioManager
from .model_manager import ModelManager
from .recording_manager import RecordingManager

__all__ = ['AudioManager', 'ModelManager', 'RecordingManager']
