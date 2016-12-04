#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship, backref

from db.model import BaseModel
from db.model.video import Video

__author__ = "htwxujian@gmail.com"


__BASE_MODEL = BaseModel.get_base_model()


# 定义Barrage对象，存储弹幕的全部相关信息
class Barrage(__BASE_MODEL):
    __tablename__ = "barrage"

    row_id = Column(String(30), primary_key=True)  # 弹幕在弹幕数据库中rowID 用于“历史弹幕”功能。
    play_timestamp = Column(String(50), nullable=False)  # 弹幕出现的时间 以秒数为单位。
    type = Column(Integer, nullable=False)  # 弹幕的模式1..3 滚动弹幕 4底端弹幕 5顶端弹幕 6.逆向弹幕 7精准定位 8高级弹幕
    font_size = Column(Integer, nullable=False)  # 字号， 12非常小,16特小,18小,25中,36大,45很大,64特别大
    font_color = Column(String(50), nullable=False)  # 字体的颜色 以HTML颜色的十位数为准
    unix_timestamp = Column(String(50), nullable=False)  # Unix格式的时间戳。基准时间为 1970-1-1 08:00:00
    pool = Column(Integer, nullable=False)  # 弹幕池 0普通池 1字幕池 2特殊池 【目前特殊池为高级弹幕专用】
    sender_id = Column(String(20), nullable=False)  # 发送者的ID，用于“屏蔽此弹幕的发送者”功能
    content = Column(Text, nullable=False)  # 弹幕内容
    # 外键信息
    video_aid = Column(String(30), ForeignKey("video.aid"), nullable=True)
    # 这样就可以使用video.barrages获得该视频的所有弹幕信息。
    video = relationship("Video", backref=backref("barrages", uselist=True, cascade="delete, all"))

    # http://docs.sqlalchemy.org/en/latest/orm/constructors.html
    # 在构建数据库行对象的时候是不会调用__init__来创建对象的，而会调用更底层的__new__。那么它们是怎么对应起来的？
    def __init__(self, play_timestamp, type, font_size, font_color, unix_timestamp, pool, sender_id, row_id, content,
                 video=None):
        self.play_timestamp = play_timestamp
        self.type = type
        self.font_size = font_size
        self.font_color = font_color
        self.unix_timestamp = unix_timestamp
        self.pool = pool
        self.sender_id = sender_id
        self.row_id = row_id
        self.content = content
        # 因为类变量中申明了video 是关于类Video的外键，所以该模块中必须import Video，否则会报错：
        # failed to locate a name ("Video" name  is not defined"). If this is a class name....
        if video is None:
            self.video = Video()
        else:
            self.video = video
        self.video_aid = None
