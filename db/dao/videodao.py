#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from db.dbutil import DBUtil
from db.model.video import Video
from db.dao.xinfandao import XinFanDao

"""
对movie数据库表进行存取操作
"""

__author__ = "htwxujian@gmail.com"


class VideoDao(DBUtil):
    # 初始化数据库的相关信息。
    DBUtil.init_db()

    @staticmethod
    def add_video(cid, title, tags, metakeywords, aid, url, season_id=None, season_index=None):
        video_info = Video(cid=cid, title=title, tags=tags, metakeywords=metakeywords, aid=aid, url=url)
        if (season_id is not None) and (season_index is not None):
            video_info.xinfan = XinFanDao.get_xinfan_by_season_id(season_id)
            video_info.season_index = season_index
        session = DBUtil.open_session()
        try:
            session.add(video_info)
            session.commit()
            return True
        except Exception as e:
            print e
            session.rollback()
            return False
        finally:
            DBUtil.close_session(session)

    @staticmethod
    def get_video_by_aid(aid):
        if aid is None:
            return None
        session = DBUtil.open_session()
        # 根据主键查询
        video_query = session.query(Video).filter(Video.aid == str(aid))
        if video_query.count() <= 0:
            DBUtil.close_session(session)
            return None
        else:
            try:
                video_info = video_query.first()
            except Exception as e:
                print e
            DBUtil.close_session(session)
            return video_info


if __name__ == "__main__":
    video = VideoDao.get_video_by_aid("6684033")
    print video.title
