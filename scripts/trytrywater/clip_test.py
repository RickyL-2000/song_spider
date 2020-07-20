# %%
import pyperclip

# %%
with open("E:/song_spider/trash/temp4.txt", 'w') as f:
    pyperclip.copy("Hello World!")
    temp = pyperclip.paste()
    # 原来这玩意的返回值就是剪贴板里的内容！妙极啦！
