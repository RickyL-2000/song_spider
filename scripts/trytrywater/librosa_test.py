# %%
import librosa
import soundfile as sf
import os

base_dir = os.getcwd()

# %%
path = r"E:\song_spider\audios\raw_audios\2(1).mp3"
y, sr = librosa.load(path)

# %%
sf.write(base_dir + '/scripts/trytrywater/librosa_test1.wav', y, sr, subtype='PCM_24')

# %%
y_out = y[20*sr: 40*sr]
sf.write(base_dir + '/scripts/trytrywater/librosa_test2.wav', y_out, sr, subtype='PCM_24')

