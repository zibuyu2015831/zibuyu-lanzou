# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: zibuyu_lanzou
author: 子不语
date: 2024/11/7
contact: 【公众号】思维兵工厂
description: 
--------------------------------------------
"""

from zibuyu_lanzou import get_direct_download_url


def main():
    response = get_direct_download_url(
        'https://wwib.lanzoul.com/iQ6S62egfmvg',
        'vArk'
    )
    # 该文件的下载直链
    print(response)


if __name__ == '__main__':
    main()
