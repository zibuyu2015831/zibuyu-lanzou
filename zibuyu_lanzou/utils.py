# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: zibuyu_lanzou
author: 子不语
date: 2024/11/07
contact: 【公众号】思维兵工厂
description: 
--------------------------------------------
"""

from fake_useragent import UserAgent
from copy import deepcopy
import mimetypes
import requests
import datetime
import logging
import json
import os
import re

# 共用请求头
HEADERS = {
    'User-Agent': UserAgent().chrome,
    # 'Referer': 'https://pan.lanzous.com',  # 可以没有
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


# 生成日志记录对象
def get_logger(
        log_name: str = "app_log",
        fmt: str = '',
        if_console: bool = True,
        base_path: str = ''
) -> logging.Logger:
    """
    获取日志记录对象
    :param log_name: 日志记录对象名称
    :param fmt: 日志格式
    :param if_console: 是否输出到终端
    :param base_path: 日志文件存放目录
    :return: 日志记录对象
    """

    today = datetime.date.today()
    formatted_date = today.strftime("%Y%m%d")

    if not fmt:
        fmt = f'%(asctime)s.%(msecs)04d | %(levelname)8s | %(message)s'

    # 创建一个Logger，默认名称：app_log
    logger = logging.getLogger(log_name)

    # 设置为日志输出级别
    logger.setLevel(logging.DEBUG)

    # 创建formatter，并设置formatter的格式
    formatter = logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S", )

    # 创建终端输出handler，为其设置格式，并添加到logger中
    if if_console:

        try:
            # 使用coloredlogs打印更好看的日志，注册即可，无需创建终端handler
            import coloredlogs

            # 自定义日志的级别颜色
            level_color_mapping = {
                'DEBUG': {'color': 'blue'},
                'INFO': {'color': 'green'},
                'WARNING': {'color': 'yellow', 'bold': True},
                'ERROR': {'color': 'red'},
                'CRITICAL': {'color': 'red', 'bold': True}
            }

            # 自定义日志的字段颜色
            field_color_mapping = dict(
                asctime=dict(color='green'),
                hostname=dict(color='magenta'),
                levelname=dict(color='white', bold=True),
                name=dict(color='blue'),
                programname=dict(color='cyan'),
                username=dict(color='yellow'),
            )

            coloredlogs.install(
                level=logging.DEBUG,
                logger=logger,
                milliseconds=True,
                datefmt='%X',
                fmt=fmt,
                level_styles=level_color_mapping,
                field_styles=field_color_mapping
            )
        except:

            # 方式一：
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)  # 设置终端的输出级别为info

            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    # 若传入base_path，即传入日志文件存放目录，则创建文件输出handler，为其设置格式，并添加到logger中
    if base_path and os.path.exists(base_path) and os.path.isdir(base_path):
        # 拼接路径
        log_dir = os.path.join(base_path, "log_file")

        # 判断路径是否存在，不存在则创建
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_path = os.path.join(log_dir, f"{formatted_date}.log")

        file_handler = logging.FileHandler(filename=file_path, mode='a', encoding='utf8', delay=False)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def name_format(name: str) -> str:
    """去除非法字符# 去除其它字符集的空白符,去除重复空白字符"""
    name = name.replace(u'\xa0', ' ').replace(u'\u3000', ' ').replace('  ', ' ')
    return re.sub(r'[$%^!*<>)(+=`\'\"/:;,?]', '', name)


def get_mime_type(file_path):
    """
    获取文件的 MIME 类型

    @param file_path: 文件的路径
    @return: 文件的 MIME 类型
    """

    # 获取文件扩展名
    # file_extension = os.path.splitext(file_path)[1]

    # 使用 mimetypes 模块获取 MIME 类型
    mime_type, _ = mimetypes.guess_type(file_path)

    return mime_type


def time_format(time_str: str) -> str:
    """输出格式化时间 %Y-%m-%d"""
    if '秒前' in time_str or '分钟前' in time_str or '小时前' in time_str:
        return datetime.datetime.today().strftime('%Y-%m-%d')
    elif '昨天' in time_str:
        return (datetime.datetime.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    elif '前天' in time_str:
        return (datetime.datetime.today() - datetime.timedelta(days=2)).strftime('%Y-%m-%d')
    elif '天前' in time_str:
        days = time_str.replace(' 天前', '')
        return (datetime.datetime.today() - datetime.timedelta(days=int(days))).strftime('%Y-%m-%d')
    else:
        return time_str


def is_name_valid(filename: str) -> bool:
    """检查文件名是否允许上传"""

    valid_suffix_list = (
        'ppt', 'xapk', 'ke', 'azw', 'cpk', 'gho', 'dwg', 'db', 'docx', 'deb', 'e', 'ttf', 'xls', 'bat',
        'crx', 'rpm', 'txf', 'pdf', 'apk', 'ipa', 'txt', 'mobi', 'osk', 'dmg', 'rp', 'osz', 'jar',
        'ttc', 'z', 'w3x', 'xlsx', 'cetrainer', 'ct', 'rar', 'mp3', 'pptx', 'mobileconfig', 'epub',
        'imazingapp', 'doc', 'iso', 'img', 'appimage', '7z', 'rplib', 'lolgezi', 'exe', 'azw3', 'zip',
        'conf', 'tar', 'dll', 'flac', 'xpa', 'lua', 'cad', 'hwt', 'accdb', 'ce',
        'xmind', 'enc', 'bds', 'bdi', 'ssf', 'it', 'gz'
    )

    return filename.split('.')[-1].lower() in valid_suffix_list


def remove_notes(html: str) -> str:
    """删除网页的注释"""
    # 去掉 html 里面的 // 和 <!-- --> 注释，防止干扰正则匹配提取数据
    # 蓝奏云的前端程序员喜欢改完代码就把原来的代码注释掉,就直接推到生产环境了 =_=
    html = re.sub(r'<!--.+?-->|\s+//\s*.+', '', html)  # html 注释
    html = re.sub(r'(.+?[,;])\s*//.+', r'\1', html)  # js 注释
    return html


def is_file_url(share_url: str) -> bool:
    """判断是否为文件的分享链接"""
    base_pat = r'https?://[a-zA-Z0-9-]*?\.?lanzou[a-z].com/.+'  # 子域名可个性化设置或者不存在
    user_pat = r'https?://[a-zA-Z0-9-]*?\.?lanzou[a-z].com/i[a-zA-Z0-9]{5,}(\?webpage=[a-zA-Z0-9]+?)?/?'  # 普通用户 URL 规则
    if not re.fullmatch(base_pat, share_url):
        return False
    if re.fullmatch(user_pat, share_url):
        return True
    # VIP 用户的 URL 很随意
    try:

        html = requests.get(share_url, headers=HEADERS).text
        html = remove_notes(html)
        return True if re.search(r'class="fileinfo"|id="file"|文件描述', html) else False
    except (requests.RequestException, Exception):
        return False


# 参考自 https://zhuanlan.zhihu.com/p/228507547
def unsbox(str_arg):
    v1 = [15, 35, 29, 24, 33, 16, 1, 38, 10, 9, 19, 31, 40, 27, 22, 23, 25, 13, 6, 11, 39, 18, 20, 8, 14, 21, 32, 26, 2,
          30, 7, 4, 17, 5, 3, 28, 34, 37, 12, 36]
    v2 = ["" for _ in v1]
    for idx in range(0, len(str_arg)):
        v3 = str_arg[idx]
        for idx2 in range(len(v1)):
            if v1[idx2] == idx + 1:
                v2[idx2] = v3

    res = ''.join(v2)
    return res


def hex_xor(str_arg, args):
    res = ''
    for idx in range(0, min(len(str_arg), len(args)), 2):
        v1 = int(str_arg[idx:idx + 2], 16)
        v2 = int(args[idx:idx + 2], 16)
        v3 = format(v1 ^ v2, 'x')
        if len(v3) == 1:
            v3 = '0' + v3
        res += v3

    return res


def calc_acw_sc__v2(html_text: str) -> str:
    arg1 = re.search(r"arg1='([0-9A-Z]+)'", html_text)
    arg1 = arg1.group(1) if arg1 else ""
    acw_sc__v2 = hex_xor(unsbox(arg1), "3000176000856006061501533003690027800375")
    return acw_sc__v2


def re_domain(url: str):
    pattern_domain = r"https?://([^/]+)"
    match = re.search(pattern_domain, url)
    return match.group(1) if match else None


def get_direct_download_url(url: str, password: str) -> str:
    """
    根据蓝奏云分享链接，获取下载直链
    @param url:
    @param password:
    @return:
    """

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
    }

    response = requests.get(url, headers=headers)

    url_match = re.search(r"url\s*:\s*'(/ajaxm\.php\?file=\d+)'", response.text).group(1)
    skdklds_match = re.search(r"var\s+skdklds\s*=\s*'([^']*)';", response.text).group(1)

    data = {
        'action': 'downprocess',
        'sign': skdklds_match,
        'p': password,
    }

    headers.update({
        "Referer": url
    })

    domain = re_domain(url)
    response2 = requests.post(f"https://{domain}{url_match}", headers=headers, data=data)
    data = json.loads(response2.text)
    full_url = data['dom'] + "/file/" + data['url']

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "sec-ch-ua": "\"Chromium\";v=\"122\", \"Not(A:Brand\";v=\"24\", \"Microsoft Edge\";v=\"122\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "cookie": "down_ip=1",
        'User-Agent': UserAgent().random,
    }

    response3 = requests.get(full_url, headers=headers, allow_redirects=False)
    redirect_url = response3.headers['Location']
    return redirect_url
