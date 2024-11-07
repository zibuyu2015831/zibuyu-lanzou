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

from typing import Union
from dataclasses import dataclass


@dataclass
class LanZouFileDetail:
    """蓝奏云文件详情"""

    request_info: str = '请求失败'
    name: str = ''
    size: str = ''
    time: str = ''
    desc: str = ''
    file_type: str = ''
    share_url: str = ''  # 分享链接
    share_pwd: str = ''  # 分享密码
    direct_url: str = ''  # 直链


@dataclass
class LanZouCookie:
    """蓝奏云cookie"""
    PHPSESSID: str
    ylogin: str
    phpdisk_info: str


@dataclass
class LanZouFolder:
    """蓝奏云文件夹信息"""
    id: Union[str, int]
    name: str
    has_pwd: bool
    desc: str


@dataclass
class LanZouFile:
    """蓝奏云文件信息"""

    id: Union[str, int] = ''
    name: str = ''  # 文件名称
    time: str = ''  # 上传时间
    size: str = ''  # 文件大小
    type: str = ''  # 文件类型
    downs: str = ''  # 下载次数
    has_pwd: bool = False  # 是否存在提取码
    has_des: bool = False  # 是否存在描述


@dataclass
class LanZouShareInfo:
    """蓝奏云分享链接信息"""

    success: bool = False
    request_msg: str = ''
    name: str = ''
    url: str = ''
    desc: str = ''
    pwd: str = ''
