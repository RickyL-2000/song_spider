# %%
import librosa
import soundfile as sf
import os
from pydub import AudioSegment

base_dir = os.getcwd()

# %%
path = r"E:\song_spider\audios\raw_audios\2(1).mp3"
y, sr = librosa.load(path)

# %%
sf.write(base_dir + '/scripts/trytrywater/librosa_test1.wav', y, sr, subtype='PCM_24')

# %%
y_out = y[20*sr: 40*sr]
sf.write(base_dir + '/scripts/trytrywater/librosa_test2.wav', y_out, sr, subtype='PCM_24')

# %%
y_out = y[20*sr: 40*sr]
sf.write(base_dir + '/scripts/trytrywater/librosa_test3.mp3', y_out, sr, subtype='PCM_24')

# %%
input_song = AudioSegment.from_wav(base_dir + '/scripts/trytrywater/librosa_test1.wav')
# %%
input_song.export(base_dir + '/scripts/trytrywater/librosa_test4.mp3', format='mp3')
