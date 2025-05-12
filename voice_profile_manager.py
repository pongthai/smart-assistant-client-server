import os
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path
from logger_config import get_logger

logger = get_logger(__name__)

class VoiceProfileManager:
    def __init__(self, profile_dir="voice_profiles"):
        logger.info("VoiceProfileManager initialized")
        self.encoder = VoiceEncoder()
        self.profile_dir = Path(profile_dir)
        self.profile_dir.mkdir(exist_ok=True)

    def list_profiles(self):
        return [f.stem for f in self.profile_dir.glob("*.npy")]

    def profile_path(self, name):
        return self.profile_dir / f"{name}.npy"

    def train_profile(self, name, wav_path):
        """
        สร้างโปรไฟล์เสียงจากไฟล์ .wav
        """
        wav = preprocess_wav(wav_path)
        embedding = self.encoder.embed_utterance(wav)
        np.save(self.profile_path(name), embedding)
        print(f"✅ โปรไฟล์เสียงของ '{name}' ถูกบันทึกแล้ว")

    def load_profiles(self):
        """
        โหลดทุกโปรไฟล์ที่บันทึกไว้ในระบบ
        """
        profiles = {}
        for file in self.profile_dir.glob("*.npy"):
            name = file.stem
            embedding = np.load(file)
            profiles[name] = embedding
        return profiles

    def identify_speaker(self, test_wav_path, threshold=0.75):
        """
        รับเสียงใหม่แล้วตรวจว่าใครคือเจ้าของเสียง
        """
        test_wav = preprocess_wav(test_wav_path)
        test_embedding = self.encoder.embed_utterance(test_wav)

        known_profiles = self.load_profiles()
        best_score = -1
        best_name = "unknown"

        for name, profile in known_profiles.items():
            
            score = np.dot(test_embedding, profile)
            logger.info(f"name={name} : score = {score}")
            if score > best_score:
                best_score = score
                best_name = name

        print(f"🔍 ความใกล้เคียงสูงสุด: {best_score:.2f} กับ '{best_name}'")
        return best_name if best_score >= threshold else "unknown"
