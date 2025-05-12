import numpy as np

emb1 = np.load("./voice_profiles/พี.npy")
emb2 = np.load("./voice_profiles/ขวัญ.npy")

print("🔍 Cosine similarity =", np.dot(emb1, emb2))
print("📊 Embedding diff =", np.abs(emb1 - emb2).sum())