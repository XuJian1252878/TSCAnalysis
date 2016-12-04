#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from db.dao.videodao import VideoDao
from db.dbutil import DBUtil
from db.model.barrage import Barrage
from util.loader.dataloader import sort_barrages

"""
对movie数据库表进行存取操作
"""

__author__ = "htwxujian@gmail.com"


class BarrageDao(object):
    # 初始化数据库的相关信息。
    DBUtil.init_db()

    """
    barrages: [(,,,,,,,), (,,,,,,,).....]
    cid: barrage对应的cid信息
    """

    @staticmethod
    def add_barrages(barrages, aid):
        video = VideoDao.get_video_by_aid(aid)
        if video is None:
            return False
        # 批量存储数据库记录。
        session = DBUtil.open_session()
        try:
            for barrage in barrages:
                b = Barrage(row_id=barrage[7], play_timestamp=barrage[0], type=barrage[1], font_size=barrage[2],
                            font_color=barrage[3], unix_timestamp=barrage[4], pool=barrage[5], sender_id=barrage[6],
                            content=barrage[8], video=video)
                # b.video = video
                session.add(b)
            session.commit()
            return True
        except Exception as e:
            print e
            session.rollback()
            return False
        finally:
            DBUtil.close_session(session)

    @staticmethod
    def add_barrage(play_timestamp, type, font_size, font_color, unix_timestamp, pool, sender_id, row_id, content, aid):
        video = VideoDao.get_video_by_aid(aid)
        if video is None:
            return False
        barrage = Barrage(play_timestamp=play_timestamp, type=type, font_size=font_size, font_color=font_color,
                          unix_timestamp=unix_timestamp, pool=pool, sender_id=sender_id,
                          row_id=row_id, content=content, video=video)
        # barrage.video = video
        print barrage.content  # 调试信息
        session = DBUtil.open_session()
        try:
            session.add(barrage)
            session.commit()
            return True
        except Exception as e:
            print e
            session.rollback()
            return False
        finally:
            DBUtil.close_session(session)

    # 查询出cid对应的所有的barrage
    # order_flag：True 按照play_timestamp升序排列
    # order_flag：False 按照play_timestamp降序排列
    @staticmethod
    def get_all_barrages_by_aid(aid, order_flag=False):
        session = DBUtil.open_session()
        try:
            barrages = session.query(Barrage).filter(Barrage.video_aid == aid).all()
            return sort_barrages(barrages)
        except Exception as e:
            print e
            session.rollback()
            return False
        finally:
            DBUtil.close_session(session)


if __name__ == "__main__":
    barrages = BarrageDao.get_all_barrages_by_aid("6671044")
    # 将 decimal 的精度设置为30
    for barrage in barrages:
        print barrage.play_timestamp
