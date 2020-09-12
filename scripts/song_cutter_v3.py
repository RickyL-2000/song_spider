# %%
# 此为用原生ffmpeg命令进行解析的裁剪脚本

# %%
import os
import json
import codecs
import time
import re
import subprocess
import threading

# %%
def load_pitch():
    """
    载入所有歌曲的乐谱（音高）数据
    :return: all_pitch 元素格式：all_pitch[i] = song_pitch
                               song_pitch[i] = [start_time, last_time, pitch]
    """
    with open(base_dir + '/alldata.json', 'r', encoding='utf-8-sig') as f:
        all_pitch = [[]]    # index从1开始
        print("loading pitch...")
        _ = 0
        for line in f.readlines():
            _ += 1
            if _ % 10000 == 0:
                print(_)
            if line[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
                line = line[codecs.BOM_UTF8:]

            json_line = json.loads(line)
            raw_notes = json_line['note']

            song_pitch = []
            try:
                notes_list = raw_notes.split()
                length = len(notes_list) // 3
                for i in range(length):
                    song_pitch.append([int(notes_list[3 * i]), int(notes_list[3 * i + 1]), int(notes_list[3 * i + 2])])
            except:
                song_pitch = None
            all_pitch.append(song_pitch)

    return all_pitch

# %%
def pitch_grouping(all_pitch, all_qrc, all_data_num, threshold=250):
    """
    将所有属于一句歌词的音符group起来
    :param all_pitch: 未group过的音符list
    :param all_qrc: 所有的歌词数据
    :param all_data_num: 总的歌曲数量(72898)
    :param threshold: 用于定位的阈值，默认250ms
    :return: all_grouped_pitch 元素格式：all_grouped_pitch[i] = song_grouped_pitch
                                       song_grouped_pitch[i] = group  # 一个group就是一句乐句
                                       group[i] = [start_time, last_time, pitch]
    """
    # NOTE: 如果有不归属于任何乐句的音高，就归为前一句
    all_grouped_pitch = [[]]
    _ = 0
    print("grouping pitch...")
    for k in range(1, all_data_num):
        _ += 1
        if _ % 10000 == 0:
            print(_)
        song_qrc = all_qrc[k]
        song_pitch = all_pitch[k]
        if song_qrc is None or song_pitch is None:
            all_grouped_pitch.append(None)
            continue

        song_grouped_pitch = []
        try:
            pre_end_idx = -1
            for i in range(len(song_qrc)):
                start_time = song_qrc[i][0][0]
                end_time = song_qrc[i][1][-1][0]    # 结束字符的开始时间
                start_idx = pre_end_idx + 1
                end_idx = start_idx + 1

                min_dist = float('inf')
                while start_idx < len(song_pitch) and abs(song_pitch[start_idx][0] - start_time) > threshold:
                    dist = abs(song_pitch[start_idx][0] - start_time)
                    if dist < min_dist:
                        min_dist = dist
                        start_idx += 1
                    else:
                        start_idx -= 1
                        break
                min_dist = float('inf')
                while end_idx < len(song_pitch) and abs(song_pitch[end_idx][0] - end_time) > threshold:
                    dist = abs(song_pitch[end_idx][0] - end_time)
                    if dist < min_dist:
                        min_dist = dist
                        end_idx += 1
                    else:
                        end_idx -= 1
                        break

                # 处理落单start
                if pre_end_idx - start_idx > 1 and len(song_grouped_pitch) > 0:
                    # 如果在当前句和前一句之间有落单的note
                    for idx in range(pre_end_idx + 1, start_idx):
                        song_grouped_pitch[-1].append(song_pitch[idx])
                elif pre_end_idx - start_idx > 1 and len(song_grouped_pitch) == 0:
                    start_idx = 0
                # 处理落单end
                pre_end_idx = end_idx
                song_grouped_pitch.append(
                    [song_pitch[i] for i in range(start_idx, end_idx + 1)]  # FIXME: index问题
                )

            assert len(song_qrc) == len(song_grouped_pitch)
        except:
            song_grouped_pitch = None

        all_grouped_pitch.append(song_grouped_pitch)

    return all_grouped_pitch


# %%
def load_qrc():
    """
    载入所有歌曲的歌词数据
    :return: all_qrc 元素格式：all_qrc[i] = song_qrc
                             song_qrc[i] = [duration, seq, phrase]
                                    duration = [start_time, end_time]   # NOTE: end_time为结束字的结束时间
                                    seq[i] = [start_time, last_time]
                                    phrase = 歌词
    """
    with open(base_dir + '/alldata.json', 'r', encoding='utf-8-sig') as f:
        all_qrc = [None]  # index从1开始
        _ = 0
        print("loading qrc...")
        for line in f.readlines():
            _ += 1
            if _ % 10000 == 0:
                print(_)
            if line[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
                line = line[codecs.BOM_UTF8:]

            json_line = json.loads(line)
            raw_qrc = json_line['qrc']
            start = raw_qrc.find("[offset:")
            start = raw_qrc.find("[", start + 1)
            end = raw_qrc.find("/>", start) - 2
            raw_qrc_list = raw_qrc[start: end].split("\n")

            # 每一首歌的
            song_qrc = []
            try:
                for sentence in raw_qrc_list:
                    sentence = sentence.strip()
                    # 总时间戳
                    start = sentence.find("[")
                    end = sentence.find("]")
                    duration = sentence[start + 1: end].split(",")
                    duration = [int(duration[0].strip("[")), int(duration[0].strip("[")) + int(duration[1].strip("]"))]

                    # 时间戳序列
                    seq = []
                    start = sentence.find("(")
                    end = sentence.find(")")
                    while start != -1:
                        node = sentence[start+1: end].split(",")
                        node = [int(node[0].strip("(")), int(node[1].strip(")"))]
                        seq.append(node)
                        start = sentence.find("(", start + 1)
                        end = sentence.find(")", end + 1)

                    # 歌词
                    phrase = ""
                    start = sentence.find("(")
                    while start != -1:
                        phrase = phrase + sentence[start - 1]
                        start = sentence.find("(", start + 1)

                    song_qrc.append([duration, seq, phrase])
            except:
                song_qrc = None
            all_qrc.append(song_qrc)

    return all_qrc

# %%
def load_song_cut_log(all_data_num, base_dir, from_audio=True):
    if from_audio:
        # song_cut_log = [[0, 0, 0]] * (all_data_num + 1)   # 不能这样！这样每个[0, 0, 0]会互相镜像！
        song_cut_log = [[0, 0, 0] for _ in range(all_data_num + 1)]
        dir_prefix = base_dir + "/audios/phrases"
        print("loading song_cut_log...")
        for i in range(1, all_data_num + 1):
            if i % 10000 == 0:
                print(i)
            for j in range(1, 4):
                if os.path.exists(dir_prefix + '/{}({})'.format(i, j)):
                    song_cut_log[i][j-1] = 1
        return song_cut_log
    else:
        with open(base_dir + "/helpers/song_cut_log.txt", "r", encoding="utf-8") as f:
            # song_cut_log = [[0, 0, 0]] * (all_data_num + 1)   # 不能这样！这样每个[0, 0, 0]会互相镜像！
            song_cut_log = [[0, 0, 0] for _ in range(all_data_num + 1)]
            for i, line in enumerate(f.readlines()):
                tmp = line.strip().split()
                for j in range(len(tmp)):
                    song_cut_log[i+1][j] = int(tmp[j])
        return song_cut_log

# %%
def write_song_cut_log(song_cut_log, all_data_num, base_dir):
    assert len(song_cut_log) == all_data_num + 1
    with open(base_dir + "/helpers/song_cut_log.txt", "w", encoding="utf-8") as f:
        for i in range(1, all_data_num + 1):
            f.write("{} {} {}\n".format(song_cut_log[i][0], song_cut_log[i][1], song_cut_log[i][2]))


# %%
def mkdir(path):
    folder = os.path.exists(path)
    if not folder:
        os.makedirs(path)
    return path

# %%
def execCmd(cmd):
    """
    :return: (stdout, stderr=None)
    """
    # r = os.popen(cmd)
    # text = r.read()
    # r.close()
    # return text
    r = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    ret = r.communicate()
    r.stdout.close()
    return ret

# %%
def getSongLen(path):
    """
    :return: 返回 microseconds
    """
    info = execCmd("ffprobe " + path)
    # pattern = re.compile("Duration: (.*?):(.*?):(.*?), start")
    # matcher = pattern.match(info[0].decode())
    text = info[0].decode()
    time_str = text[text.find("Duration") + 10: text.find(", start")]
    length = time2sec(time_str)
    return length * 1000

# %%
def time2sec(time_str):
    start = 0
    end = time_str.find(':')
    ret = int(time_str[start: end]) * 3600
    start = end + 1
    end = time_str.find(':', start)
    ret += int(time_str[start: end]) * 60
    start = end + 1
    ret = float(time_str[start:]) + float(ret)
    return ret


# %%
def song_cut(song_idx, all_qrc, all_grouped_pitch, song_cut_log, base_dir, threshold=500):
    song_qrc = all_qrc[song_idx]
    song_pitch = all_grouped_pitch[song_idx]
    if song_qrc is None or song_pitch is None:
        print("{}.mp3 --- loading failed".format(song_idx), end='  ')
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        return
    # for i in range(1, 4):     TODO: debug
    for i in range(3, 4):
        if song_cut_log[song_idx][i-1]:
            # check if this song has been processed
            continue
        file_name = r"{}({}).mp3".format(song_idx, i)
        if os.path.exists(base_dir + "/audios/raw_audios/" + file_name):
            try:
                # 创建新目录
                mkdir(base_dir + '/audios/phrases/{}({})'.format(song_idx, i))

                # 获取音频时长
                song_length = getSongLen(base_dir + '/audios/raw_audios/"' + file_name + '"')

                # 查看是否为有效音频
                # print("check validation")
                assert song_length >= song_pitch[-1][-1][0] + song_pitch[-1][-1][1] - song_pitch[0][0][0]
                # print("check validation done")

                for j in range(len(song_qrc)):
                    duration = song_qrc[j][0]

                    # 分割
                    start_time = max(duration[0] - threshold, 0)
                    end_time = min(duration[1] + threshold, song_length)
                    last_time = end_time - start_time
                    cmd = 'ffmpeg -i {} -ss 00:{:02d}:{:02.2f} -t 00:{:02d}:{:02.2f} {}'.format(
                        base_dir + '/audios/raw_audios/"' + file_name + '"',
                        start_time // 60000,
                        start_time % 60000 / 1000,
                        last_time // 60000,
                        last_time % 60000 / 1000,
                        base_dir + '/audios/phrases/"{}({})"/{}.mp3'.format(song_idx, i, j)
                    )
                    ret = execCmd(cmd)
                    if ret[1] is not None:
                        continue

                    # 存歌词和音符
                    content = {
                        'duration': [max(duration[0] - threshold, 0), min(duration[1] + threshold, song_length)],
                        'qrc': {
                            'seq': song_qrc[j][1],
                            'phrase': song_qrc[j][2]
                        },
                        'pitch': song_pitch[j]
                    }
                    with open(base_dir + '/audios/phrases/{}({})/{}.json'.format(song_idx, i, j),
                              'w', encoding='utf-8') as f:
                        json.dump(content, f)

                print("{}({}).mp3 --- successfully processed".format(song_idx, i), end='  ')
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                time.sleep(0.1)

            except:
                print("{}({}).mp3 --- processing failed".format(song_idx, i), end='  ')
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                time.sleep(0.1)

# %%
def main(all_qrc, all_grouped_pitch, song_cut_log, all_data_num, base_dir, start_point=1):
    for song_idx in range(start_point, all_data_num):
        song_cut(song_idx, all_qrc, all_grouped_pitch, song_cut_log, base_dir, threshold=300)

# %%
def main_threaded(all_qrc, all_grouped_pitch, song_cut_log, all_data_num, base_dir, start_point=1, max_threads=10):
    # 先生成queue
    song_idx_queue = [idx for idx in range(all_data_num, start_point, -1)]

    def process_queue():
        # 弹出queue
        # 调用cutter
        while True:
            try:
                song_idx = song_idx_queue.pop()
            except IndexError:
                break

            song_cut(song_idx, all_qrc, all_grouped_pitch, song_cut_log, base_dir, threshold=300)

    threads = []
    while threads or song_idx_queue:
        for thread in threads:
            if not thread.is_alive():
                threads.remove(thread)
        while len(threads) < max_threads and song_idx_queue:
            thread = threading.Thread(target=process_queue)
            thread.setDaemon(True)
            thread.start()
            threads.append(thread)
        time.sleep(1)

# %%
def test():
    song_idx = 2
    song_cut(song_idx, all_qrc, all_grouped_pitch, song_cut_log, base_dir, threshold=300)
    # file_name = r"2(1).mp3"
    # length = getSongLen(base_dir + '/audios/raw_audios/"' + file_name + '"')
    # print(length)


# %%
if __name__ == "__main__":
    base_dir = '/home/renyi/ry/lrq'
    all_data_num = 72898
    all_qrc = load_qrc()
    all_pitch = load_pitch()
    all_grouped_pitch = pitch_grouping(all_pitch, all_qrc, all_data_num, threshold=250)

    song_cut_log = load_song_cut_log(all_data_num, base_dir, from_audio=True)

    # test()
    # main(all_qrc, all_grouped_pitch, all_data_num, base_dir, start_point=8)
    main_threaded(all_qrc, all_grouped_pitch, song_cut_log, all_data_num, base_dir, start_point=44800, max_threads=20)

# %%
# trytrywater
"""
threshold = 300
song_idx = 2
song_qrc = all_qrc[song_idx]
file_name = r"{}({}).mp3".format(song_idx, 1)
song_pitch = all_grouped_pitch[song_idx]
mkdir(base_dir + '/audios/phrases/{}({})'.format(song_idx, 1))

i = 1
j = 0
duration = song_qrc[j][0]
length = getSongLen(base_dir + '/audios/raw_audios/"' + file_name + '"')
start_time = max(duration[0] - threshold, 0)
end_time = min(duration[1] + threshold, length)
last_time = end_time - start_time
cmd = 'ffmpeg -i {} -ss 00:{:02d}:{:02.2f} -t 00:{:02d}:{:02.2f} {}'.format(
    base_dir + '/audios/raw_audios/"' + file_name + '"',
    start_time // 60000,
    start_time % 60000 / 1000,
    last_time // 60000,
    last_time % 60000 / 1000,
    base_dir + '/audios/phrases/"{}({})"/{}.mp3'.format(song_idx, i, j)
)

ret = execCmd(cmd)
"""
