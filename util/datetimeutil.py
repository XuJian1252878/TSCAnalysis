#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import math
import time

"""
文件存取的操作，将弹幕数据写入本地文件中。
"""

__author__ = "htwxujian@gmail.com"


class DateTimeUtil(object):
    # 获得当前的时间戳
    @staticmethod
    def get_cur_timestamp(time_format):
        return time.strftime(time_format, time.localtime(time.time()))

    # 格式化原弹幕数据中的playtimestamp为xxminutexxs的格式
    # 参数：play_timestamp 以秒为单位
    @staticmethod
    def format_barrage_play_timestamp(play_timestamp):
        timestamp = float(play_timestamp)
        minutes = int(math.floor(timestamp / 60))
        seconds = int(math.floor(timestamp % 60))
        format_timestamp = unicode(str(minutes) + u" minutes " + str(seconds) + u" seconds")
        return format_timestamp
