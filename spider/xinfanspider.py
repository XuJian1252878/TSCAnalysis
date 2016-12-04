#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
1. 获取新番剧集的弹幕信息
步骤：
1） 获取新番列表
2） 获取新番下的剧集、标签信息
3） 获取新番剧集的弹幕信息
"""

from spider import BarrageSpider
from util.loggerutil import Logger
import json
import math
from db.model.xinfan import XinFan
import re
from db.dao.xinfandao import XinFanDao
from spider.bilibilispider import BilibiliSpider

__author__ = "htwxujian@gmail.com"
logger = Logger("video-url-spider.log").get_logger()


class XinFanSpider(BarrageSpider):

    def __init__(self):
        super(XinFanSpider, self).__init__()
        # b站新番列表的获取api链接 'http://bangumi.bilibili.com/web_api/season/index?page=1&version=0&index_type=0&pagesize=30'
        self.xin_fan_base_url = 'http://bangumi.bilibili.com/web_api/season/index'
        self.page_size = 30  # 每一个新番页面对应的新番个数
        self.bilibili_spider = BilibiliSpider()

    # 构建新番api的获取连接信息（新番分为多页显示）
    # 输入：page 当前页面的下标
    #      page_size 每一个页面显示多少新番，这个数b站一致默认是30，不用改变
    def __construct_xin_fan_list_url(self, page, page_size=30):
        if page is None:
            return 'http://bangumi.bilibili.com/web_api/season/index?page=1&version=0&index_type=0&pagesize=30'
        return self.xin_fan_base_url + '?page=' + str(page) + '&version=0&index_type=0&pagesize=' + str(page_size)

    # 获取新番列表的总页数
    def __get_xin_fan_page_count(self, xin_fan_count, page_size=30):
        return int(math.ceil(xin_fan_count * 1.0 / page_size))

    # 获取当前新番的总数
    def __get_xin_fan_count(self):
        res_dict = self.__get_xin_fan_json_data(page=None)
        return int(res_dict['result']['count'])

    # 获取新番相关的json response数据
    def __get_xin_fan_json_data(self, page):
        json_data = self.get_response_content(self.__construct_xin_fan_list_url(page=page))
        res_dict = json.loads(json_data, encoding='utf-8')
        if (res_dict['code'] != 0) or (res_dict['message'] != 'success'):
            return None
        return res_dict

    # 将新番的dict转化为新番对象
    def __convert_dict_to_xin_fan(self, xin_fan_list):
        xin_fans = []
        for item in xin_fan_list:
            cover = item.get('cover', None)  # 新番的封面图片
            is_finish = item.get('is_finish', None)  # 新番是否完结，1表示正在连载，2表示已完结
            newest_ep_index = item.get('newest_ep_index', None)  # 当前新番连载的最新集数
            pub_time = item.get('pub_time', None)  # 可能是最新集数的发布时间
            season_id = item.get('season_id', None)  # 新番的id信息
            title = item.get('title', None)  # 新番的名称
            total_count = item.get('total_count', None)  # 这个暂时不知道意义
            url = item.get('url', None)  # 进入新番列表的连接
            week = item.get('week', None)  # 这个暂时不知道意义
            xin_fan = XinFan(cover, is_finish, newest_ep_index, pub_time, season_id, title, total_count, url, week)
            # 设置新番的tags
            xin_fan.tags = self.__get_xin_fan_tags(self.get_response_content(url))
            xin_fans.append(xin_fan)
        return xin_fans

    # 获得新番的标签信息
    def __get_xin_fan_tags(self, page_html):
        pattern = re.compile(r'<span class="info-style-item">(.*?)</span>', re.S)
        match = re.findall(pattern, page_html)
        if match is None:
            return None
        tags = '\t'.join(match)
        return tags

    # 获取新番的所有剧集连接，关于aid的剧集链接。
    def __get_anime_url(self, page_html):
        pattern = re.compile(r'<li class="v1-bangumi-list-part-child".*?<a class="v1-short-text" href="(.*?)".*?</li>', re.S)
        match = re.findall(pattern, page_html)
        if match is None:
            return None
        # 接下来访问链接，获取av号格式的视频链接信息
        anime_aid_urls = []
        for item_url in match:
            page_html = self.get_response_content(item_url)
            pattern = re.compile(r'</time>.*?<a href="(.*?)" class="v-av-link" target="_blank" >.*?</a>', re.S)
            match = re.search(pattern, page_html)
            if match is None:
                anime_aid_urls.append(None)
                continue
            anime_aid_urls.append(match.groups()[0])
        return anime_aid_urls  # 返回剧集的链接列表信息，或者是None

    # 获取新番列表的所有信息
    def get_xin_fan_info(self):
        xin_fan_list = []  # 新番的基本信息列表
        # 1. 首先用默认的连接请求新番列表
        xin_fan_count = self.__get_xin_fan_count()
        # 2. 获取新番剧集的页数，page_size默认是30
        xin_fan_page_count = self.__get_xin_fan_page_count(xin_fan_count)
        # xin_fan_page_count = 1
        for index in xrange(1, xin_fan_page_count + 1):
            json_data = self.get_response_content(self.__construct_xin_fan_list_url(page=str(index)))
            res_dict = json.loads(json_data, encoding='utf-8')
            if res_dict is None:
                continue
            xin_fan_list += self.__convert_dict_to_xin_fan(res_dict['result']['list'])

        xin_fan_info_list = []
        for xin_fan in xin_fan_list:
            xin_fan_info_list.append((xin_fan.season_id, xin_fan.url))

        # 3.将所有新番的基本信息写入数据库。
        XinFanDao.add_xin_fans(xin_fan_list)

        for index in xrange(0, len(xin_fan_info_list)):
            xin_fan = xin_fan_info_list[index]
            # 4. 获得新番所有剧集的av链接信息
            page_html = self.get_response_content(xin_fan[1])
            anime_aid_urls = self.__get_anime_url(page_html)
            for av_url in anime_aid_urls:
                self.bilibili_spider.start_spider_barrage(video_url=av_url, is_save_to_db=True,
                                                          season_id=xin_fan[0], season_index=index)
        return xin_fan_list


if __name__ == '__main__':
    xin_fan_spider = XinFanSpider()
    xin_fan_list = xin_fan_spider.get_xin_fan_info()
    print xin_fan_list

    # print xin_fan_spider.get_xin_fan_tags(xin_fan_spider.get_response_content('http://bangumi.bilibili.com/anime/5070/'))
    # anime_list =  xin_fan_spider.get_anime_url(xin_fan_spider.get_response_content('http://bangumi.bilibili.com/anime/5070/'))
    # print len(anime_list)
    # print anime_list