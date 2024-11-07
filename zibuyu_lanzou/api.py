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

import re
import os
import time
import logging
import requests
from datetime import datetime
from urllib3 import disable_warnings
from typing import List, Optional, Union, Callable
from urllib3.exceptions import InsecureRequestWarning

from fake_useragent import UserAgent
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

from .type import LanZouCookie, LanZouShareInfo, LanZouFolder, LanZouFile, LanZouFileDetail
from .utils import get_logger, time_format, is_name_valid, name_format, get_mime_type, is_file_url, calc_acw_sc__v2, \
    remove_notes


class LanZouApi(object):
    """
    蓝奏云 API
    """

    _timeout = 15  # 每个请求的超时(不包含下载响应体的用时)
    _max_size = 100  # 单个文件大小上限 MB

    def __init__(
            self,
            log_file_path: str = '',
            cookies: Optional[LanZouCookie] = None,
            logger: Optional[logging.Logger] = None,
    ):
        """

        @param cookies: LanZouCookie实例化对象
        @param logger: 日志记录对象
        @param log_file_path: 日志文件保存路径，为空表达不保存
        """

        if logger and isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = get_logger(log_name='lanzou_api', base_path=log_file_path)

        self._session = requests.session()
        self._cookies: Optional[LanZouCookie] = cookies

        if isinstance(cookies, LanZouCookie):
            self._session.cookies.update({
                'PHPSESSID': cookies.PHPSESSID,
                'ylogin': cookies.ylogin,
                'phpdisk_info': cookies.phpdisk_info,
            })

            self._uid = cookies.ylogin  # uid 用于上传文件时的参数

        self._headers = {
            'User-Agent': UserAgent().random,
            'Referer': 'https://pc.woozooo.com/mydisk.php',
            'Accept-encoding': 'gzip, deflate, br, zstd',
            'Accept': '*/*',
            'Origin': 'https://pc.woozooo.com',
            'Accept-Language': 'zh-CN,zh;q=0.9',  # 提取直连必需设置这个，否则拿不到数据
        }

        self._host_url = 'https://pan.lanzouo.com'
        self._doupload_url = 'https://pc.woozooo.com/doupload.php'
        self._account_url = 'https://pc.woozooo.com/account.php'
        self._mydisk_url = 'https://pc.woozooo.com/mydisk.php'

        disable_warnings(InsecureRequestWarning)  # 全局禁用 SSL 警告

    def check_cookie(self):
        """检查是否传入了可用的 cookie"""

        if not isinstance(self._cookies, LanZouCookie):
            self.logger.error('cookies 参数错误, 请检查后重试。三个 cookie 字段必须都存在')
            exit(1)

        if not all([self._cookies.PHPSESSID, self._cookies.ylogin, self._cookies.phpdisk_info]):
            self.logger.error('cookies 参数错误, 请检查后重试。三个 cookie 字段必须都存在')
            exit(1)

    @staticmethod
    def _all_possible_urls(url: str) -> List[str]:
        """蓝奏云的主域名有时会挂掉, 此时尝试切换到备用域名"""
        available_domains = [
            'lanzouw.com',  # 鲁ICP备15001327号-7, 2021-09-02
            'lanzoui.com',  # 鲁ICP备15001327号-6, 2020-06-09
            'lanzoux.com'  # 鲁ICP备15001327号-5, 2020-06-09
        ]

        return [url.replace('lanzouo.com', d) for d in available_domains]

    def _get(self, url, need_check_cookie: bool = True, **kwargs):
        """
        尝试使用所有可能的域名进行请求，直到成功为止。
        :param url: 请求的 url
        :param need_check_cookie: 是否需要检查 cookie
        :param kwargs: 其他参数
        :return: requests.Response
        """

        if need_check_cookie:
            self.check_cookie()

        for possible_url in self._all_possible_urls(url):
            try:
                kwargs.setdefault('timeout', self._timeout)
                kwargs.setdefault('headers', self._headers)
                return self._session.get(possible_url, verify=False, **kwargs)
            except (ConnectionError, requests.RequestException):
                self.logger.debug(f"Get 请求失败，尝试另一个 domain")

        return None

    def _post(self, url, data, headers: Optional[dict] = None, need_check_cookie: bool = True, **kwargs) -> Optional[
        requests.Response]:

        if need_check_cookie:
            self.check_cookie()

        for possible_url in self._all_possible_urls(url):
            try:
                kwargs.setdefault('timeout', self._timeout)
                if not headers:
                    headers = self._headers
                response = self._session.post(possible_url, data, verify=False, headers=headers, **kwargs)
                if response.status_code == 200 and response.content:
                    return response
            except (ConnectionError, requests.RequestException):
                self.logger.debug(f"Post 请求失败，尝试另一个 domain")

        return

    def get_share_info(self, fid, is_file=True) -> LanZouShareInfo:
        """获取文件(夹)提取码、分享链接"""

        post_data = {'task': 22, 'file_id': fid} if is_file else {'task': 18, 'folder_id': fid}  # 获取分享链接和密码用
        f_info = self._post(self._doupload_url, post_data)
        if not f_info:
            return LanZouShareInfo(
                request_msg='网络异常'
            )
        else:
            f_info = f_info.json()['info']

        # id 有效性校验
        if ('f_id' in f_info.keys() and f_info['f_id'] == 'i') or ('name' in f_info.keys() and not f_info['name']):
            return LanZouShareInfo(request_msg='fid错误')

        # onof=1 时，存在有效的提取码; onof=0 时不存在提取码，但是 pwd 字段还是有一个无效的随机密码
        pwd = f_info['pwd'] if f_info['onof'] == '1' else ''
        if 'f_id' in f_info.keys():  # 说明返回的是文件的信息
            url = f_info['is_newd'] + '/' + f_info['f_id']  # 文件的分享链接需要拼凑
            file_info = self._post(self._doupload_url, {'task': 12, 'file_id': fid})  # 文件信息
            if not file_info:
                return LanZouShareInfo(request_msg='网络异常')
            name = file_info.json()['text']  # 无后缀的文件名(获得后缀又要发送请求,没有就没有吧,尽可能减少请求数量)
            desc = file_info.json()['info']
        else:
            url = f_info['new_url']  # 文件夹的分享链接可以直接拿到
            name = f_info['name']  # 文件夹名
            desc = f_info['des']  # 文件夹描述
        return LanZouShareInfo(success=True, request_msg='请求成功', name=name, url=url, desc=desc, pwd=pwd)

    def set_passwd(self, fid, passwd='', is_file=True) -> bool:
        """
        设置网盘文件(夹)的提取码
        id 无效或者 id 类型不对应仍然返回成功 :(

        @param fid: 文件id或文件夹id
        @param passwd: 待设置的密码，文件夹提取码长度 0-12 位  文件提取码 2-6 位；为空表示去除密码；
        @param is_file: 是否是文件；默认为 True
        @return:
        """

        passwd_status = 0 if passwd == '' else 1  # 是否开启密码

        if passwd_status == 1 and is_file and (len(passwd) < 2 or len(passwd) > 6):
            self.logger.warning(f"提取码长度不符合要求，文件的提取码长度为 2-6 位提取码，当前提取码为 {passwd}")
            return False

        if passwd_status == 1 and not is_file and (len(passwd) < 1 or len(passwd) > 12):
            self.logger.warning(f"提取码长度不符合要求，文件夹的提取码长度为 1-12 位提取码，当前提取码为 {passwd}")
            return False

        if is_file:
            post_data = {"task": 23, "file_id": fid, "shows": passwd_status, "shownames": passwd}
        else:
            post_data = {"task": 16, "folder_id": fid, "shows": passwd_status, "shownames": passwd}
        result = self._post(self._doupload_url, post_data)
        if not result:
            return False
        return True if result.json()['zt'] == 1 else False

    def get_dir_list(self, folder_id=-1) -> List[LanZouFolder]:
        """获取子文件夹列表"""

        folder_list = []

        post_data = {'task': 47, 'folder_id': folder_id, 'vei': 'VFBQUg1fUghQBA9fAFo='}
        headers = self._headers.copy()
        headers['content-type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        resp = self._post(self._doupload_url + "?uid=" + str(self._uid), post_data)  # 上传文件时需要 uid 参数

        if not resp:
            return folder_list

        try:
            for folder in resp.json()['text']:
                folder_list.append(
                    LanZouFolder(
                        id=folder['fol_id'],
                        name=folder['name'],
                        has_pwd=True if int(folder['onof']) == 1 else False,
                        desc=folder['folder_des'].strip('[]')
                    ))
        except:
            self.logger.warning(f"获取文件夹列表，解析返回数据时发生错误，返回值: 【{resp.text}】")
        finally:
            return folder_list

    def _set_dir_info(self, folder_id, folder_name, desc='') -> bool:
        """重命名文件夹及其描述"""
        # 不能用于重命名文件，id 无效仍然返回成功
        folder_name = name_format(folder_name)
        post_data = {'task': 4, 'folder_id': folder_id, 'folder_name': folder_name, 'folder_description': desc}
        result = self._post(self._doupload_url, post_data)
        if not result:
            return False
        return True if result.json()['zt'] == 1 else False

    def set_desc(self, fid, desc, is_file=True) -> bool:
        """设置文件(夹)描述"""

        if is_file:
            # 文件描述一旦设置了值，就不能再设置为空
            post_data = {'task': 11, 'file_id': fid, 'desc': desc}
            result = self._post(self._doupload_url, post_data)
            if not result:
                return False
            elif result.json()['zt'] != 1:
                return False
            return True
        else:
            # 文件夹描述可以置空
            info = self.get_share_info(fid, is_file=False)
            if not info.success:
                return False
            return self._set_dir_info(fid, info.name, desc)

    def get_file_list(self, folder_id: Union[str, int] = -1) -> List[LanZouFile]:
        """获取文件列表"""

        page = 1
        file_list: List[LanZouFile] = []
        while True:
            post_data = {'task': 5, 'folder_id': folder_id, 'pg': page, 'vei': "VFBQUg1fUghQBA9fAFo="}
            resp = self._post(self._doupload_url, post_data)
            if not resp:  # 网络异常，重试
                continue
            else:
                resp = resp.json()
            if resp["info"] == 0:
                break  # 已经拿到了全部的文件信息
            else:
                page += 1  # 下一页
            # 文件信息处理
            for file in resp["text"]:
                file_list.append(LanZouFile(
                    id=file['id'],
                    name=file['name_all'].replace("&amp;", "&"),
                    time=time_format(file['time']),  # 上传时间
                    size=file['size'].replace(",", ""),  # 文件大小
                    type=file['name_all'].split('.')[-1],  # 文件类型
                    downs=file['downs'],  # 下载次数
                    has_pwd=True if int(file['onof']) == 1 else False,  # 是否存在提取码
                    has_des=True if int(file['is_des']) == 1 else False  # 是否存在描述
                ))
        return file_list

    def delete_file_or_folder(self, fid, is_file=True) -> bool:
        """
        把网盘的文件、无子文件夹的文件夹放到回收站
        @param fid:
        @param is_file:
        @return:
        """

        post_data = {'task': 6, 'file_id': fid} if is_file else {'task': 3, 'folder_id': fid}
        result = self._post(self._doupload_url, post_data)
        if not result:
            return False
        return True if result.json()['zt'] == 1 else False

    def __upload_small_file(
            self,
            file_path: str,
            folder_id: Union[str, int] = -1,
            *, callback: Optional[Callable] = None,
            need_delete: bool = False,
            uploaded_handler: Optional[Callable] = None
    ) -> List[LanZouFile]:
        """
        上传不超过 max_size 的文件
        @param file_path: 本地文件路径
        @param folder_id: 文件夹 id，默认为 -1，表示根目录
        @param need_delete: 上传完成是否删除
        @param callback: 上传进度回调函数，参数为已上传大小，单位为字节
        @param uploaded_handler: 上传完成后的回调函数，参数为文件信息对象，返回值为是否删除文件
        @return:
        """

        file_obj_list: List[LanZouFile] = []

        if not os.path.isfile(file_path):
            self.logger.warning(f"文件 {file_path} 不存在")
            return file_obj_list

        if not is_name_valid(os.path.basename(file_path)):  # 不允许上传的格式
            self.logger.warning(f"文件 {file_path} 的后缀不允许上传，请使用其他后缀重新命名")
            return file_obj_list

        # 文件已经存在同名文件就删除
        filename = name_format(os.path.basename(file_path))
        file_list = self.get_file_list(folder_id)

        for file_obj in file_list:
            if file_obj.name == filename:
                self.logger.info(f"文件 {file_path} 已存在同名文件，删除同名文件")
                self.delete_file_or_folder(file_obj.id)

        # MultipartEncoderMonitor 每上传 8129 bytes数据调用一次回调函数，问题根源是 httplib 库
        # issue : https://github.com/requests/toolbelt/issues/75
        # 上传完成后，回调函数会被错误的多调用一次(强迫症受不了)。因此，下面重新封装了回调函数，修改了接受的参数，并阻断了多余的一次调用
        self._upload_finished_flag = False  # 上传完成的标志

        def _call_back(read_monitor):
            if callback is not None:
                if not self._upload_finished_flag:
                    callback(filename, read_monitor.len, read_monitor.bytes_read)
                if read_monitor.len == read_monitor.bytes_read:
                    self._upload_finished_flag = True

        self.logger.debug(f'正在上传文件: 【{file_path}】')
        last_modified_date = datetime.now().strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)')

        with open(file_path, 'rb') as file:
            post_data = {
                "task": "1",
                "vie": "2",
                "ve": "2",
                "id": "WU_FILE_0",
                "name": filename,
                'type': get_mime_type(file_path),
                'lastModifiedDate': last_modified_date,
                "folder_id_bb_n": str(folder_id),
                "upload_file": (filename, file, 'application/octet-stream')
            }

            post_data = MultipartEncoder(post_data)
            tmp_header = self._headers.copy()
            tmp_header['Content-Type'] = post_data.content_type

            monitor = MultipartEncoderMonitor(post_data, _call_back)
            result = self._post('https://pc.woozooo.com/html5up.php', data=monitor, headers=tmp_header, timeout=3600)

        if not result:  # 网络异常
            return file_obj_list

        try:
            resp_json = result.json()

            if resp_json["zt"] != 1:
                self.logger.debug(f'文件上传失败，响应数据是：【{result.text}】')
                return file_obj_list  # 上传失败

            file_info_list = resp_json["text"]

            for file_dict in file_info_list:
                obj = LanZouFile(
                    id=file_dict.get("id"),
                    name=file_dict.get("name"),
                    time=file_dict.get('time'),  # 上传时间
                    size=file_dict.get('size'),  # 文件大小
                    type=file_dict.get("icon"),  # 文件类型
                    downs=file_dict.get("downs"),  # 下载次数
                    has_pwd=False,  # 是否存在提取码
                    has_des=False,  # 是否存在描述
                )
                file_obj_list.append(obj)

            self.logger.info('上传文件成功')

            if uploaded_handler is not None and callable(uploaded_handler):
                for obj in file_obj_list:
                    uploaded_handler(obj.id, is_file=True)  # 对已经上传的文件再进一步处理

            if need_delete:
                os.remove(file_path)
        except:
            self.logger.error('上传文件时发生错误', exc_info=True)
        finally:
            return file_obj_list

    def upload_file(
            self,
            file_path,
            folder_id=-1,
            *, callback: Optional[Callable] = None,
            uploaded_handler: Optional[Callable] = None
    ) -> Optional[List[LanZouFile]]:

        """
        解除限制上传文件

        def callback(file_name, total_size, now_size):
            print(f"\r文件名:{file_name}, 进度: {now_size}/{total_size}")
            ...

        def uploaded_handler(fid, is_file):
            if is_file:
                self.set_desc(fid, '...', is_file=True)
                ...

        @param file_path:
        @param folder_id:
        @param callback: 用于显示上传进度的回调函数
        @param uploaded_handler: uploaded_handler 用于进一步处理上传完成后的文件, 对大文件而已是处理文件夹(数据块默认关闭密码)
        @return:
        """

        if not os.path.isfile(file_path):
            self.logger.warning(f"文件 {file_path} 不存在")
            return

            # 单个文件不超过 max_size 直接上传
        if os.path.getsize(file_path) <= self._max_size * 1048576:
            return self.__upload_small_file(file_path, folder_id, callback=callback, uploaded_handler=uploaded_handler)

        self.logger.warning(f"文件 {file_path} 大小超过 {self._max_size} MB，无法直接上传")

    def logout(self) -> bool:
        """
        登陆失败
        @return: bool，退出成功返回True，否则返回False
        """

        html = self._get(self._account_url, params={'action': 'logout'})
        if not html:
            self.logger.error('退出登陆失败')
            return False

        # 重置请求session
        self._session = requests.Session()

        self.logger.info('成功退出登陆')
        return True if '退出系统成功' in html.text else False

    def get_file_info_by_url(self, share_url, pwd='') -> LanZouFileDetail:
        """
        获取文件各种信息(包括下载直链)
        :param share_url: 文件分享链接
        :param pwd: 文件提取码(如果有的话)
        """

        if not is_file_url(share_url):  # 非文件链接返回错误
            return LanZouFileDetail(request_info='URL错误', share_pwd=pwd, share_url=share_url)

        first_page = self._get(share_url, need_check_cookie=False)  # 文件分享页面(第一页)
        if not first_page:
            return LanZouFileDetail(request_info='网络错误', share_pwd=pwd, share_url=share_url)

        if "acw_sc__v2" in first_page.text:
            # 在页面被过多访问或其他情况下，有时候会先返回一个加密的页面，其执行计算出一个acw_sc__v2后放入页面后再重新访问页面才能获得正常页面
            # 若该页面进行了js加密，则进行解密，计算acw_sc__v2，并加入cookie
            acw_sc__v2 = calc_acw_sc__v2(first_page.text)
            self._session.cookies.set("acw_sc__v2", acw_sc__v2)
            self.logger.debug(f"Set Cookie: acw_sc__v2={acw_sc__v2}")
            first_page = self._get(share_url, need_check_cookie=False)  # 文件分享页面(第一页)
            if not first_page:
                return LanZouFileDetail(request_info='网络错误', share_pwd=pwd, share_url=share_url)

        first_page = remove_notes(first_page.text)  # 去除网页里的注释

        if '文件取消' in first_page or '文件不存在' in first_page:
            return LanZouFileDetail(request_info='文件已取消分享', share_pwd=pwd, share_url=share_url)

        # 这里获取下载直链 304 重定向前的链接
        try:
            if 'id="pwdload"' in first_page or 'id="passwddiv"' in first_page:  # 文件设置了提取码时
                if len(pwd) == 0:
                    # 没给提取码直接退出
                    return LanZouFileDetail(
                        request_info='文件密码错误', share_pwd=pwd,
                        share_url=share_url
                    )

                    # data : 'action=downprocess&sign=AGZRbwEwU2IEDQU6BDRUaFc8DzxfMlRjCjTPlVkWzFSYFY7ATpWYw_c_c&p='+pwd,
                sign = re.search(r"var skdklds = '(.*?)';", first_page).group(1)
                post_data = {'action': 'downprocess', 'sign': sign, 'p': pwd}
                link_info = self._post(self._host_url + '/ajaxm.php', post_data)  # 保存了重定向前的链接信息和文件名
                second_page = self._get(share_url, need_check_cookie=False)  # 再次请求文件分享页面，可以看见文件名，时间，大小等信息(第二页)
                if not link_info or not second_page.text:
                    return LanZouFileDetail(request_info='网络错误', share_pwd=pwd, share_url=share_url)
                link_info = link_info.json()
                second_page = remove_notes(second_page.text)
                # 提取文件信息
                f_name = link_info['inf'].replace("*", "_")
                f_size = re.search(r'大小.+?(\d[\d.,]+\s?[BKM]?)<', second_page)
                f_size = f_size.group(1).replace(",", "") if f_size else '0 M'
                f_time = re.search(r'class="n_file_infos">(.+?)</span>', second_page)
                f_time = time_format(f_time.group(1)) if f_time else time_format('0 小时前')
                f_desc = re.search(r'class="n_box_des">(.*?)</div>', second_page)
                f_desc = f_desc.group(1) if f_desc else ''
            else:  # 文件没有设置提取码时,文件信息都暴露在分享页面上
                para = re.search(r'<iframe.*?src="(.+?)"', first_page).group(1)  # 提取下载页面 URL 的参数
                # 文件名位置变化很多
                f_name = re.search(r"<title>(.+?) - 蓝奏云</title>", first_page) or \
                         re.search(r'<div class="filethetext".+?>([^<>]+?)</div>', first_page) or \
                         re.search(r'<div style="font-size.+?>([^<>].+?)</div>', first_page) or \
                         re.search(r"var filename = '(.+?)';", first_page) or \
                         re.search(r'id="filenajax">(.+?)</div>', first_page) or \
                         re.search(r'<div class="b"><span>([^<>]+?)</span></div>', first_page)
                f_name = f_name.group(1).replace("*", "_") if f_name else "未匹配到文件名"
                # 匹配文件时间，文件没有时间信息就视为今天，统一表示为 2020-01-01 格式
                f_time = re.search(r'>(\d+\s?[秒天分小][钟时]?前|[昨前]天\s?[\d:]+?|\d+\s?天前|\d{4}-\d\d-\d\d)<',
                                   first_page)
                f_time = time_format(f_time.group(1)) if f_time else time_format('0 小时前')
                # 匹配文件大小
                f_size = re.search(r'大小.+?(\d[\d.,]+\s?[BKM]?)<', first_page)
                f_size = f_size.group(1).replace(",", "") if f_size else '0 M'
                f_desc = re.search(r'文件描述.+?<br>\n?\s*(.*?)\s*</td>', first_page)
                f_desc = f_desc.group(1) if f_desc else ''
                first_page = self._get(self._host_url + para, need_check_cookie=False)
                if not first_page:
                    return LanZouFileDetail(
                        request_info='网络错误',
                        name=f_name, time=f_time,
                        size=f_size, desc=f_desc,
                        share_pwd=pwd, share_url=share_url
                    )

                first_page = remove_notes(first_page.text)
                # 一般情况 sign 的值就在 data 里，有时放在变量后面
                sign = re.search(r"'sign':(.+?),", first_page).group(1)
                if len(sign) < 20:  # 此时 sign 保存在变量里面, 变量名是 sign 匹配的字符
                    sign = re.search(rf"var {sign}\s*=\s*'(.+?)';", first_page).group(1)
                post_data = {'action': 'downprocess', 'sign': sign, 'ves': 1}

                # 某些特殊情况 share_url 会出现 webpage 参数, post_data 需要更多参数
                # https://github.com/zaxtyson/LanZouCloud-API/issues/74
                # https://github.com/zaxtyson/LanZouCloud-API/issues/81
                if "?webpage=" in share_url:
                    ajax_data = re.search(r"var ajaxdata\s*=\s*'(.+?)';", first_page).group(1)
                    web_sign = re.search(r"var a?websigna?\s*=\s*'(.+?)';", first_page).group(1)
                    web_sign_key = re.search(r"var c?websignkeyc?\s*=\s*'(.+?)';", first_page).group(1)
                    post_data = {'action': 'downprocess', 'signs': ajax_data, 'sign': sign, 'ves': 1,
                                 'websign': web_sign, 'websignkey': web_sign_key}

                link_info = self._post(self._host_url + '/ajaxm.php', post_data)
                if not link_info:
                    return LanZouFileDetail(
                        request_info='网络错误',
                        time=f_time, size=f_size,
                        desc=f_desc, name=f_name,
                        share_pwd=pwd, share_url=share_url
                    )
                link_info = link_info.json()
        except AttributeError as e:  # 正则匹配失败
            self.logger.error(e, exc_info=True)
            return LanZouFileDetail(request_info='直链获取失败', )

        # 这里开始获取文件直链
        if link_info['zt'] != 1:  # 返回信息异常，无法获取直链
            return LanZouFileDetail(
                request_info='直链获取失败',
                name=f_name, time=f_time,
                size=f_size, desc=f_desc,
                share_pwd=pwd,
                share_url=share_url
            )

        fake_url = link_info['dom'] + '/file/' + link_info['url']  # 假直连，存在流量异常检测
        download_page = self._get(fake_url, need_check_cookie=False, allow_redirects=False)
        if not download_page:
            return LanZouFileDetail(
                request_info='网络错误',
                name=f_name, time=f_time,
                size=f_size, desc=f_desc,
                share_pwd=pwd, share_url=share_url
            )

        download_page.encoding = 'utf-8'
        download_page_html = remove_notes(download_page.text)
        if '网络异常' not in download_page_html:  # 没有遇到验证码
            direct_url = download_page.headers['Location']  # 重定向后的真直链
        else:  # 遇到验证码，验证后才能获取下载直链
            try:
                file_token = re.findall("'file':'(.+?)'", download_page_html)[0]
                file_sign = re.findall("'sign':'(.+?)'", download_page_html)[0]
                check_api = 'https://vip.d0.baidupan.com/file/ajax.php'
                post_data = {'file': file_token, 'el': 2, 'sign': file_sign}
                time.sleep(2)  # 这里必需等待2s, 否则直链返回 ?SignError
                resp = self._post(check_api, post_data)
                direct_url = resp.json()['url']
                if not direct_url:
                    return LanZouFileDetail(
                        request_info='直链获取失败',
                        time=f_time, size=f_size,
                        desc=f_desc, name=f_name,
                        share_pwd=pwd, share_url=share_url
                    )

            except IndexError as e:
                self.logger.error(e, exc_info=True)
                return LanZouFileDetail(request_info='直链获取失败', )

        f_type = f_name.split('.')[-1]
        return LanZouFileDetail(
            request_info='请求成功',
            name=f_name, size=f_size,
            desc=f_desc, share_pwd=pwd,
            file_type=f_type, time=f_time,
            share_url=share_url, direct_url=direct_url
        )

    def get_file_info_by_id(self, file_id) -> LanZouFileDetail:
        """通过 id 获取文件信息"""
        info = self.get_share_info(file_id)
        if not info.success:
            return LanZouFileDetail(request_info='请求失败')
        return self.get_file_info_by_url(info.url, info.pwd)

    def get_direct_url_by_url(self, share_url, pwd='') -> str:
        """通过分享链接获取下载直链"""
        file_info = self.get_file_info_by_url(share_url, pwd)
        if file_info.direct_url:
            return file_info.direct_url

    def get_direct_url_by_id(self, file_id) -> str:
        """登录用户通过id获取直链"""
        info = self.get_share_info(file_id, is_file=True)  # 能获取直链，一定是文件
        return self.get_direct_url_by_url(info.url, info.pwd)
