# %%
import numpy as np
import pyworld as pw
import soundfile as sf
import matplotlib.pyplot as plt
import librosa

# %%
base_dir = r"E:\song_spider\\"


# %%
# soundfile
def read_wav(base_dir):
    x, fs = sf.read(base_dir + r"audios\separate\18291\vocals.wav")
    y = (x[:, 0] + x[:, 1]) / 2
    return y, fs


y, fs = read_wav(base_dir)

# print(fs)   # 44100
# y.shape == 13063596

# %%
# 用librosa读入
def read_wav_librosa(base_dir):
    y, fs = librosa.load(base_dir + r"audios\separate\18291\vocals.wav", dtype=float)
    return y, fs


y, fs = read_wav_librosa(base_dir)


# %%
# 滤波
# 采样频率2000，剔除660以上，2*660/2000 = 0.66
from scipy import signal
b, a = signal.butter(8, 0.4, btype='low')
filted_y = signal.filtfilt(b, a, y)
filted_y = filted_y.copy(order='C')

# %%
x = np.linspace(0, 13063596/44100, 13063596)
plt.plot(x, y)
plt.xlabel('time')
plt.ylabel('frequency')
plt.show()

# %%
# x = np.linspace(0, 13063596/44100, 13063596)
plt.plot(x, filted_y)
plt.xlabel('time')
plt.ylabel('frequency')
plt.show()


# %%
# f0, sp, ap = pw.wav2world(x, fs)
# t 以0.005s为间隔
f0, t = pw.dio(y, fs)
# print(f0.shape)
# print(t.shape)


# %%
# 提取滤波后的频率谱
filted_f0, filted_t = pw.dio(filted_y, fs)

# %%
# 画出人声频率曲线
plt.plot(t, f0)
plt.xlabel('time')
plt.ylabel('frequency')
plt.title("base frequency")
plt.show()

"""
有没有什么比较好的滤波方法？
"""

# %%
# 滤波后的图像
plt.plot(filted_t, filted_f0)
plt.xlabel('time')
plt.ylabel('frequency')
plt.title("base frequency")
plt.show()


# %%
# 删除0赫兹数据
"""
for i in range(f0.shape[0]):
    if i == 0:
        continue
    if f0[i] == 0.0:
        f0[i] = f0[i - 1]

plt.plot(t[5500:20000], f0[5500:20000])
plt.xlabel('time')
plt.ylabel('frequency')
plt.show()
"""

# %%
# 制作 音高 - 频率 的映射
# C1 - F6
def pitch2freq(pitch):
    return 440 * 2 ** ((pitch - 69) / 12)

# %%
# 制作频率乐谱
# 如果不降八度，距离=229
# 如果降了八度，距离=127
import codecs
import json


def extract_notes(base_dir):
    str_notes = ""
    with open(base_dir + r"sample.json", encoding='UTF-8') as sample:
        notes = sample.readline()
        if notes[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
            notes = notes[codecs.BOM_UTF8:]
        json_notes = json.loads(notes)
        str_notes = json_notes["note"]

    # 将乐谱做成list
    notes = str_notes.split()
    raw_notes_list = []
    length = int(len(notes) / 3)
    for i in range(length):
        raw_notes_list.append([int(notes[3*i]), int(notes[3*i+1]), int(notes[3*i+2])])

    # 按照 5ms 的间隔做成list[time_position, frequency]
    notes_list = []
    time_idx = 0
    note_idx = 0
    raw_notes_list_len = len(raw_notes_list)
    while note_idx < raw_notes_list_len:
        cur_f = 0.0
        while time_idx < raw_notes_list[note_idx][0]:
            notes_list.append([time_idx / 1000, cur_f])
            time_idx += 5
        cur_f = pitch2freq(raw_notes_list[note_idx][2] - 12)     # NOTE: 降八度!!
        while time_idx < raw_notes_list[note_idx][0] + raw_notes_list[note_idx][1]:
            notes_list.append([time_idx / 1000, cur_f])
            time_idx += 5
        note_idx += 1

    return np.array(notes_list)


notes_list = extract_notes(base_dir)
score = notes_list[:, 1]

# len(note_list) == 35700

# %%
# 画出乐谱
plt.plot(notes_list[:, 0], notes_list[:, 1])
plt.xlabel('time')
plt.ylabel('frequency')
plt.title('good score')
plt.show()


# %%
# 制作对照组代码

def extract_bad_notes(base_dir):
    str_notes = ""
    with open(base_dir + r"sample.json", encoding='UTF-8') as sample:
        temp = [next(sample) for x in range(3)]
        notes = temp[2]
        if notes[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
            notes = notes[codecs.BOM_UTF8:]
        json_notes = json.loads(notes)
        str_notes = json_notes["note"]

    # 将乐谱做成list
    notes = str_notes.split()
    raw_notes_list = []
    length = int(len(notes) / 3)
    for i in range(length):
        raw_notes_list.append([int(notes[3*i]), int(notes[3*i+1]), int(notes[3*i+2])])

    # 按照 5ms 的间隔做成list[time_position, frequency]
    notes_list = []
    time_idx = 0
    note_idx = 0
    raw_notes_list_len = len(raw_notes_list)
    while note_idx < raw_notes_list_len:
        cur_f = 0.0
        while time_idx < raw_notes_list[note_idx][0]:
            notes_list.append([time_idx / 1000, cur_f])
            time_idx += 5
        cur_f = pitch2freq(raw_notes_list[note_idx][2])
        while time_idx < raw_notes_list[note_idx][0] + raw_notes_list[note_idx][1]:
            notes_list.append([time_idx / 1000, cur_f])
            time_idx += 5
        note_idx += 1

    return np.array(notes_list)


bad_notes_list = extract_bad_notes(base_dir)
bad_score = bad_notes_list[:, 1]

# len(note_list) == 35700

# %%
# 画出对照组乐谱
plt.plot(bad_notes_list[:, 0], bad_notes_list[:, 1])
plt.xlabel('time')
plt.ylabel('frequency')
plt.show()


# %%
# 计算距离
# 因为直接整首歌进行match需要将近16G的内存，因此分batch进行match
# FIXME: 分batch失败了，因为这个可能是整首歌的位置偏移等问题...
# FIXME: 同一首歌的音频文件，居然bad的距离比该歌曲的notes短？？？
# FIXME: 感觉问题出在f0不准确
# TODO: 解决f0不准确的问题
from dtw import *

# broadcast
if len(f0) < len(score):
    f0 = np.append(f0, np.zeros(len(score) - len(f0)))
else:
    score = np.append(score, np.zeros(len(f0) - len(score)))
length = len(f0)

# alignment = dtw(f0, notes_list[:, 1])

distances = []
batch_size = 20000
for i in range(0, length, batch_size):
    alignment = dtw(f0[i: min(i + batch_size, len(f0))], score[i: min(i + batch_size, len(f0))])
    distances.append(alignment.normalizedDistance)

distance = sum(distances)

# %%
# 计算对照组距离

# broadcast
if len(f0) < len(bad_score):
    f0 = np.append(f0, np.zeros(len(bad_score) - len(f0)))
else:
    bad_score = np.append(bad_score, np.zeros(len(f0) - len(bad_score)))
length = len(f0)

# alignment = dtw(f0, notes_list[:, 1])

bad_distances = []
batch_size = 20000
for i in range(0, length, batch_size):
    alignment = dtw(f0[i: min(i + batch_size, len(f0))], bad_score[i: min(i + batch_size, len(f0))])
    bad_distances.append(alignment.normalizedDistance)

bad_distance = sum(bad_distances)

# %%
"""
fast dtw
"""
# 试试fastdtw?

# %%
# 原 notes 计算
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
base_f = []
good = []
for i in range(len(f0)):
    base_f.append([t[i], f0[i]])
for i in range(notes_list.shape[0]):
    good.append([notes_list[i, 0], notes_list[i, 1]])
base_f = np.array(base_f)
good = np.array(good)
fast_distance, path = fastdtw(base_f, good, dist=euclidean)

# %%
# bad notes 计算


# %%
# trytrywater
with open(base_dir + r"sample.json", encoding='utf-8') as myfile:
    head = [next(myfile) for x in range(2)]
