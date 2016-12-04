#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import codecs
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.model import BaseModel

"""
数据库操作模块，提供连接数据库，打开session等数据库操作的基本方法。
"""

__author__ = "htwxujian@gmail.com"


class DBUtil(object):
    # 数据库连接字符串，由于弹幕中常常含有特殊的字符串，因此可能需要 ?charset=utf8mb4 来解决。
    # 参考链接：http://docs.sqlalchemy.org/en/latest/dialects/mysql.html#dialect-mysql
    __CONN_STRING = "mysql+mysqlconnector://root:18917878003@localhost:3306/barragedb?charset=utf8mb4&use_unicode=0"
    # create a configured "Session" class
    __SESSION = None
    __ENGINE = None
    __BASE_MODEL = BaseModel.get_base_model()

    # 构建数据库链接
    @staticmethod
    def construct_conn_str(db_type, db_driver, db_user_name, db_pass, hostname, port, db_name):
        # '数据库类型+数据库驱动名称://用户名:口令@机器地址:端口号/数据库名'
        __CONN_STRING = db_type + "+" + db_driver + "://" + db_user_name + ":" \
                        + db_pass + "@" + hostname + ":" + str(port) + "/" + db_name
        DBUtil.__SESSION = None
        DBUtil.__ENGINE = None

    @staticmethod
    def create_engine(conn_str=None):
        if conn_str is None:
            conn_str = DBUtil.__CONN_STRING
        if DBUtil.__ENGINE is None:
            # engine 作为编程语言与数据库的接口，conn_str 中需要一致 数据库与 编程语言的字符编码，这样才不会出现乱码。这里双方都是
            # utf8mb4
            DBUtil.__ENGINE = create_engine(conn_str, echo=True)
        return DBUtil.__ENGINE  # engine对象和session对象都可作用于数据库的增删改查操作。

    # 创建一个配置好的Session类，产生session对象，用于数据库的增删改查。
    @staticmethod
    def create_configured_session():
        if DBUtil.__SESSION is None:
            engine = DBUtil.create_engine()
            return sessionmaker(bind=engine)
        return DBUtil.__SESSION

    # 打开一个新的session，数据库的表创建，增删改查操作都要在session中进行。
    @staticmethod
    def open_session():
        configured_session = DBUtil.create_configured_session()
        session = configured_session()
        return session

    # 关闭之前新建立的session。
    @staticmethod
    def close_session(session):
        if session is not None:
            session.close()

    @staticmethod
    @contextmanager
    def my_scoped_session():
        """Provide a transactional scope around a series of operations."""
        session = DBUtil.create_configured_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            print e
            session.rollback()
        finally:
            session.close()

    # 初始化数据库，创建数据库表等。
    @staticmethod
    def init_db():
        # 数据库包装这一层，存在大量的encode操作，使用的是database的charset，在数据库端指定了使用utf8mb4编码，那么外部模块与
        # 数据库连接时，要使用相同的编码，修改数据库数据时也应该使用相同的编码。
        # 而Python的codec模块不知道utf8mb4这种表述，所以需要使用别名。make python understand 'utf8mb4' as an alias for 'utf8'。
        codecs.register(lambda name: codecs.lookup('utf8') if name == 'utf8mb4' else None)
        # 创建对应的数据库表。
        engine = DBUtil.create_engine()
        DBUtil.__BASE_MODEL.metadata.create_all(engine)

if __name__ == "__main__":
    db_util = DBUtil()
    db_util.init_db()
