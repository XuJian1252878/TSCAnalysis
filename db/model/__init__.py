#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
数据库实体类的基类，所有的数据库实体类都继承于该类，在整个数据库操作中只能有一个该实体。
比如在两个basemodel实体中都有barrage table的信息时，会报错。
会出现这个错误：sqlalchemy Table 'barrage' is already defined for this MetaData instance.
"""

from sqlalchemy.ext.declarative import declarative_base

__author__ = "htwxujian@gmail.com"


class BaseModel(object):

    __BASE_MODEL = None

    @classmethod
    def get_base_model(cls):
        if cls.__BASE_MODEL is None:
            cls.__BASE_MODEL = declarative_base()
        return cls.__BASE_MODEL

