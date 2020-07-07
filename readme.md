# README

每行对应一个json格式数据，表示一首歌曲。'note' 表示melody，'qrc' 表示歌词部分。
数据来源于某 卡拉OK app，可能有版权问题，请不要在互联网上传播。

## 数据格式

1.qrc歌词以qrc为扩展名的歌词文件，可以在最新版的QQ音乐播放器中同步显示。这种歌词文件可以用来实现卡拉OK功能，并且歌词显示精准定位到逐字，使歌词同步显示更准确，彻底改善传统LRC歌词显示不准确的问题。当然这种歌词文件较大，编辑较困难。
2.qrc歌词是一个XML格式的文件。
```
格式：<?xml version="1.0" encoding="utf-8"?>
<QrcInfos>
<QrcHeadInfo SaveTime="****" Version="100"/>
<LyricInfo LyricCount="1">
<Lyric_1 LyricType="1" LyricContent="
3歌词主题与LRC歌词类似
1.标识标签：
[ti:歌曲名]
[ar:歌手名]
[al:专辑名]
[by:歌词的制作人]
[offset:时间补偿值]
2.时间标签：
[开始ms,持续ms]歌词一(开始ms,持续ms)歌词一(开始ms,持续ms)
时间标签需位于某行歌词中的每个字。当播放时播放器就会播对应时间标签的每个字，从而达到卡拉OK歌词逐字定位。
3.相对于lrc格式的歌词来说，qrc歌词较为复杂，精准度要求高，歌词制作也很容易出现偏差（qq音乐部分歌词有时间不准确或出现时间差错现象）。但是在歌词的精准度上，远远超过lrc歌词。只是现在目前能支持qrc歌词的音dao乐播放器不多，大部分还只能支持lrc格式。
```

## 文件内容

* pairs.7z - 数据集的压缩包
* alldata.json - 所有数据
* sample.json - 从总数据集中抽样13条的数据，用于方便查看数据的结构
* scripts - python脚本
    * extraction.py - 用于提取歌曲名称、演唱者、歌词等
    * audio_process.py - 用于处理音频
* raw_data - 存放未经处理的文本数据
    * raw_titles.txt - 所有歌曲的名称，未人工处理，有些是数字代号，有些是乱码
    * raw_singers.txt - 所有歌曲的演唱者
    * raw_lyrics.txt - 所有歌曲的歌词
* helpers
    * digits_titles.txt - 记录了所有title是一串数字的歌曲在raw_titles.txt中的行号
* audios - 存放所有音频文件
    * separate - 存放用spleeter输出的vocal和bgm
        * - 命令：spleeter separate -i "E:\song_spider\audios\raw_audios\18291.mp3" -o ..\audios\separate\
    * raw_audios - 存放所有未经处理的音频文件
        * -
* processed_data - 存放人工处理后的文本数据
    * titles.txt
    * singers.txt
