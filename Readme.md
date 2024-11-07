# 蓝奏云API逆向

蓝奏云是一个很小众的网盘工具，少有的不对存储总量和下载速度作限制的网盘。

这个Python包实现对文件的上传、创建分享、设置密码、获取下载直链等功能。

使用方式：

- 网址登陆，获取三个cookie信息：`PHPSESSID` 、`phpdisk_info`、 `ylogin`；

![image-20241107183724280](assets/Readme/image-20241107183724280.png)

- 导入`LanZouApi` 和 `LanZouCookie` 两个类，传入获取到的cookie，进行实例化；

```python
from zibuyu_lanzou import LanZouApi, LanZouCookie

cookie = LanZouCookie(
	PHPSESSID="xxx",
	ylogin="xxx",
	phpdisk_info="xxx",
)

handler = LanZouApi(cookie)
```

之后就可以使用 `handler` 对象进行操作。

如果你有一个蓝奏云的分享链接，只是想单纯地获取下载直链，也可以使用 `get_direct_download_url`方法：



```python
from zibuyu_lanzou import get_direct_download_url

response = get_direct_download_url(
    share_url='https://wwib.lanzoul.com/iQ6S62egfmvg',
    password='vArk'
)

print(response) # 该文件的下载直链
```













