#! /usr/bin/env python2.7
# -*- coding: utf-8 -*-

import codecs
from spider import Spider
from util.loggerutil import Logger
import re

logger = Logger("file_download.log", console_only=True).get_logger()


class FileDownload(Spider):

    def __init__(self):
        super(FileDownload, self).__init__()

    # 获取视频的下载链接信息。
    # 从这网站获取b站的视频下载链接信息：http://www.ibilibili.com/video/av5394711/
    def get_download_links(self, video_link):
        html_content = self.get_response_content(video_link)
        # 原来的正则匹配语句：<ul\sclass="list-group"\sid="download">.*?<a\shref ="(.*?)".*?>视频下载.*?</a>.*?
        # <a\shref ="(.*?)".*?>MP3下载.*?</a>.*?</ul> 因为包含有中文，一致匹配不上，具体原因未知。
        pattern = re.compile(r'<ul\sclass="list-group"\sid="download">.*?'
                             r'<a href ="(.*?)".*?>.*?</a>.*?<a href ="(.*?)".*?>MP3.*?</a>.*?</ul>', re.S)
        match = re.search(pattern, html_content)
        if match is None:
            return None
        video_download_link = match.group(1)
        mp3_download_link = match.group(2)
        return video_download_link, mp3_download_link

    # 下载指定文件
    # download_url: 文件下载的连接信息
    # download_url：下载文件的文件名（应包含文件保存的路径，不写路径的话默认当前目录。）
    # headers：爬取网页相关的网页头信息
    def download_file(self, download_url, file_name, headers=None):
        if headers is None:
            headers = self.headers
        req = self.construct_req_by_get(download_url, headers)
        res = self.access_url(req, self.timeout)
        chunk = 1000 * 1024  # 1kb为缓冲区下载文件
        download_process = 0
        with codecs.open(file_name, "wb") as output_file:
            while True:
                content_buffer = res.read(chunk)
                download_process += chunk
                logger.debug("download process: " + str(download_process / 1024) + " kb")
                if not content_buffer:
                    logger.info(file_name + u" download success!!")
                    break
                output_file.write(content_buffer)

if __name__ == "__main__":
    file_download = FileDownload()
    # file_download.download_file(download_url="http://down.360safe.com/se/360se8.1.1.216.exe", file_name="360se8.1.1.216.exe")
    video_download_link, mp3_download_link = file_download.get_download_links("http://www.ibilibili.com/video/av5394711/")
    print video_download_link, mp3_download_link
    file_download.download_file(mp3_download_link, "av5394711.mp3")
    file_download.download_file(video_download_link, "av5394711.mp4")
