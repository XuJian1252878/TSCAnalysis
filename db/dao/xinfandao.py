#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from db.dbutil import DBUtil
from db.model.xinfan import XinFan

__author__ = "htwxujian@gmail.com"

"""
对XinFan数据表进行操作
"""

class XinFanDao(DBUtil):
    # 初始化数据库的相关信息。
    DBUtil.init_db()

    # 添加一个新番的基本信息
    @staticmethod
    def add_xin_fan(xin_fan):
        session = DBUtil.open_session()
        try:
            session.add(xin_fan)
            session.commit()
            return True
        except Exception as e:
            print e
            session.rollback()
            return False
        finally:
            DBUtil.close_session(session)

    # 批量插入新番信息
    @staticmethod
    def add_xin_fans(xin_fans):
        session = DBUtil.open_session()
        try:
            for xin_fan in xin_fans:
                session.add(xin_fan)
            session.commit()
            return True
        except Exception as e:
            print e
            session.rollback()
            return False
        finally:
            DBUtil.close_session(session)

    # 根据主键查询新番的基本信息
    @staticmethod
    def get_xinfan_by_season_id(season_id):
        if season_id is None:
            return None
        session = DBUtil.open_session()
        # 根据主键查询
        xin_fan_query = session.query(XinFan).filter(XinFan.season_id == season_id)
        if xin_fan_query.count() <= 0:
            DBUtil.close_session(session)
            return None
        else:
            xin_fan_info = xin_fan_query.one()
            DBUtil.close_session(session)
            return xin_fan_info
