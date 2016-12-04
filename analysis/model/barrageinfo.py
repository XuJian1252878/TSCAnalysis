#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import logging

"""
针对弹幕数据的每一次加载来说，如弹幕数据重新加载，那么原来的数据全部清空。
记录弹幕加载过程中的信息，比如发表弹幕的全部用户id等，用于产生相似度矩阵。
"""


class BarrageInfo(object):
    __ALL_SENDER_ID = None

    # 记录本次弹幕数据中所有的用户id信息。
    # 参数：barrage_list 列表，每一个元素就是barrage对象。
    @classmethod
    def collect_barrage_sender_id(cls, barrage_list):
        # 首先清空上一次发弹幕用户的id数据。
        cls.__ALL_SENDER_ID = []
        for barrage in barrage_list:
            if barrage.sender_id not in cls.__ALL_SENDER_ID:
                cls.__ALL_SENDER_ID.append(barrage.sender_id)

    # 获得当前的弹幕用户id的总数量
    @classmethod
    def get_barrage_sender_count(cls):
        if cls.__ALL_SENDER_ID is None:
            return 0
        return len(cls.__ALL_SENDER_ID)

    # 根据输入的用户id，返回该用户id在当前全部用户id下的下标，目的在于构建时间窗口的矩阵。
    # 当用户id列表不存在，或者输入的用户id不在当前列表中，那么返回None。
    @classmethod
    def get_sender_id_index(cls, sender_id):
        if cls.__ALL_SENDER_ID is None:
            return None
        try:
            user_id_index = cls.__ALL_SENDER_ID.index(sender_id)
            return user_id_index
        except ValueError as e:
            logging.info(e.message)
            return None
