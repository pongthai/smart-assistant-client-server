import os
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

def create_voice_profiles(input_folder="known_voices", output_file="voice_profiles.npy"):
    encoder = VoiceEncoder()
    profiles = {}

    for file in os.listdir(input_folder):
        if file.endswith(".wav"):
            name = os.path.splitext(file)[0]
            file_path = os.path.join(input_folder, file)

            print(f"Processing {name} from {file_path} ...")
            wav = preprocess_wav(file_path)
            embedding = encoder.embed_utterance(wav)
            profiles[name] = embedding

    # Save embeddings to a file
    np.save(output_file, profiles)
    print(f"✅ Voice profiles saved to {output_file}")

if __name__ == "__main__":
    create_voice_profiles()

