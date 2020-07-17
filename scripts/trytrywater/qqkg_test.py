# %%
import requests
from bs4 import BeautifulSoup as bs4
import urllib3

# %%
url = r"http://kg.qq.com/accompanydetail/index.html?mid=00000iyp0RWqZo"
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; U; Android 9; zh-cn; PAR-AL00 Build/HUAWEIPAR-AL00) AppleWebKit/533.1 (KHTML, '
                  'like Gecko) Mobile Safari/533.1  Hippy/1.0 qua/V1_AND_KG_7.4.28_278_70124_X qmkege/7.4.28 ',
    'Connection': 'close',
    'Host': 'node.kg.qq.com',
    'Cookie': 'openkey=JxEAC17yxxcAD0LwAAAAIJHktUVije0Gz9Qlu5gVE/rIlRKrOCJ5Oa9E4tS1FZxe; NetworkInfo=1; '
              'openid=oc2eXjm_SMwXzRKiWnJg_o3y6RVc; extroInfo=1|0|0|0|0; uid=782409670; midasPfKey=pfKey; '
              'midasPf=wechat_wx-2001-android-2011; midasSessionId=hy_gameid; midasSessionType=wc_actoken; '
              'masteruid=0; udid=8614470559196445439; midasPayToken=; opentype=1 '
}
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
page = requests.get(url, headers=headers, verify=False)
soup = bs4(page, 'html.parser')
