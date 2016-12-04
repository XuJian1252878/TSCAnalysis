#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from sqlalchemy import Column, String, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship, backref

from db.model import BaseModel
from db.model.xinfan import XinFan

__author__ = "htwxujian@gmail.com"


__BASE_MODEL = BaseModel.get_base_model()


# 定义movie对象，保存movie的id，标题，以及链接等信息
class Video(__BASE_MODEL):
    __tablename__ = "video"

    cid = Column(String(30), nullable=False)  # 视频对应的弹幕cid
    title = Column(Text, nullable=False)  # 视频的标题信息。
    tags = Column(Text, nullable=False)  # 视频的分类标签信息，格式为：一级标签\t二级标签...
    metakeywords = Column(Text, nullable=False)  # 视频的标签信息，格式为：标签1\t标签2\t标签3...
    aid = Column(String(30), primary_key=True)  # 视频的aid
    url = Column(Text, nullable=False)  # 视频的网址链接
    season_index = Column(Integer, nullable=True)
    xinfan_season_id = Column(String(30), ForeignKey('xinfan.season_id'), nullable=True)
    xinfan = relationship("XinFan", backref=backref("videos", uselist=True, cascade="delete, all"))

    def __init__(self, cid=None, title=None, tags=None, metakeywords=None, aid=None, url=None, xinfan=None):
        self.cid = cid
        self.title = title
        self.tags = tags
        self.metakeywords = metakeywords
        self.aid = aid
        self.url = url
        if xinfan is None:
            self.xinfan = XinFan()
        else:
            self.xinfan = xinfan
        self.xinfan_season_id = None
        self.season_index = None



