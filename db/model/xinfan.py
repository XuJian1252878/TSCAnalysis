#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
新番信息的实体类
"""

from sqlalchemy import Column, String, Text, Integer

from db.model import BaseModel

__author__ = "htwxujian@gmail.com"

__BASE_MODEL = BaseModel.get_base_model()


class XinFan(__BASE_MODEL):
    __tablename__ = 'xinfan'
    cover = Column(Text, nullable=True)
    is_finish = Column(Integer, nullable=True)
    newest_ep_index = Column(Text, nullable=True)
    pub_time = Column(Integer, nullable=True)
    season_id = Column(String(30), primary_key=True)
    title = Column(Text, nullable=True)
    total_count = Column(Integer, nullable=True)
    url = Column(Text, nullable=True)
    week = Column(String(30), nullable=True)
    tags = Column(Text, nullable=True)

    def __init__(self, cover=None, is_finish=None, newest_ep_index=None, pub_time=None, season_id=None, title=None,
                 total_count=None, url=None, week=None):
        self.cover = cover  # 新番的封面图片
        self.is_finish = is_finish  # 新番是否完结，1表示正在连载，2表示已完结
        self.newest_ep_index = newest_ep_index  # 当前新番连载的最新集数
        self.pub_time = pub_time  # 可能是最新集数的发布时间
        self.season_id = season_id  # 新番的id信息
        self.title = title  # 新番的名称
        self.total_count = total_count  # 这个暂时不知道意义
        self.url = url  # 进入新番列表的连接
        self.week = week  # 这个暂时不知道意义
        self.tags = None  # 这个番剧的tag，以\t字符串分割