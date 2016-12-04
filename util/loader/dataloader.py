#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import codecs
import datetime
import os
import re
from decimal import Decimal, getcontext
from gensim import corpora

from analysis.model.barrageinfo import BarrageInfo
from analysis.model.dictconfig import DictConfig
from db.model.barrage import Barrage
from util.datetimeutil import DateTimeUtil
from util.fileutil import FileUtil

"""
从本地的txt弹幕文件（本地项目根目录data/local/文件夹下。）中加载弹幕数据。或者是从数据库中加载弹幕数据。
"""


def __sort_barrages_by_play_timestamp(barrage):
    # 由于play_timestamp字符串时间戳的小数位置不定，所以用Decial将字符串转化为数字
    # 将 decimal 的精度设置为30
    getcontext().prec = 30
    return Decimal(barrage.play_timestamp)


# order_flag：True 按照play_timestamp降序排列
# order_flag：False 按照play_timestamp升序排列
def sort_barrages(barrages, order_flag=False):
    barrages = sorted(barrages, key=__sort_barrages_by_play_timestamp, reverse=order_flag)
    return barrages


# 从本地的txt文件中读取弹幕的信息，
# 参数：txt_file_path  本地弹幕文件的路径。
#      order_flag True 返回的按照play_timestamp降序排列；False 按照play_timestamp升序排列
def get_barrage_from_txt_file(txt_file_path, order_flag=False):
    # 首先 初始化我们需要的字典信息，如停用词词典、情感词典等等，为将来的处理步骤做准备。
    DictConfig.build_dicts()

    barrages = []
    with codecs.open(txt_file_path, "rb", "utf-8") as input_file:
        for barrage in input_file:
            # 弹幕信息的格式：play_timestamp type font_size font_color unix_timestamp pool sender_id row_id content
            split_info = barrage.strip().split(u"\t")
            if len(split_info) < 9:
                # 有些弹幕数据没有内容(content)这一列的内容，对于这些弹幕过滤掉。
                continue
            barrage = Barrage(split_info[0], split_info[1], split_info[2], split_info[3], split_info[4], split_info[5],
                              split_info[6], split_info[7], split_info[8])
            barrages.append(barrage)
    barrages = sort_barrages(barrages, order_flag)
    # barrages = sorted(barrages, key=lambda barrage: barrage.play_timestamp)
    # 将 barrage 中所有的 sender_id 信息存储起来。以备后期生成相似度矩阵。
    BarrageInfo.collect_barrage_sender_id(barrages)
    return barrages


# 将本地txt弹幕文件中数据读出，排好序，并将play_timestamp转化为 xx minute xx s的格式，再写入当前的文件夹下
def gen_sorted_barrage_file(barrage_file_path):
    barrages = get_barrage_from_txt_file(barrage_file_path)  # 弹幕信息已经按照降序进行排好序。
    sorted_file_name = FileUtil.get_cid_from_barrage_file_path(barrage_file_path) + "-sorted.txt"
    with codecs.open(sorted_file_name, "wb", "utf-8") as output_file:
        for barrage in barrages:
            play_time_stamp = unicode(str(float(barrage.play_timestamp)))
            barrage_str = DateTimeUtil.format_barrage_play_timestamp(play_time_stamp) + u"\t" + play_time_stamp \
                          + u"\t" + barrage.type + u"\t" + barrage.font_size + u"\t" + barrage.font_color + u"\t" \
                          + barrage.unix_timestamp + u"\t" + barrage.pool + u"\t" + barrage.sender_id + u"\t" \
                          + barrage.row_id + u"\t" + barrage.content + u"\n"
            output_file.write(barrage_str)
    return barrages


# 解析出xml文件中的弹幕信息，文件名称必须是以 cid.xml命名的，否则无法读取弹幕信息。
def parse_barrage_xml_to_txt(xml_file_path):
    # 获取xml文件中的全部内容。
    with codecs.open(xml_file_path, "rb", "utf-8") as input_file:
        content = []
        for line in input_file:
            content.append(line)
    content = u"\n".join(content)
    # 弹幕出现的播放时间，弹幕类型，字体大小，字体颜色，弹幕出现的unix时间戳，弹幕池，弹幕创建者id，弹幕id
    pattern = re.compile(r'<d p="(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?)">(.*?)</d>', re.S)
    barrages = re.findall(pattern, content)
    if len(barrages) <= 0:
        return None
    txt_file_name = FileUtil.get_cid_from_barrage_file_path(xml_file_path) + ".txt"
    with codecs.open(txt_file_name, "wb", "utf-8") as output_file:
        for barrage in barrages:
            output_file.write(u"\t".join(barrage) + u"\n")
    return barrages


# 解析出bilibili直播的弹幕数据。
def get_barrage_from_live_text_file(file_path):
    # 首先 初始化我们需要的字典信息，如停用词词典、情感词典等等，为将来的处理步骤做准备。
    DictConfig.build_dicts()

    with codecs.open(file_path, "rb", "utf-8") as input_file:
        (folder, file_name) = os.path.split(file_path)
        barrage_start_datetime_str = file_name.split(".")[0] + " 12:00:00"  # 每场围棋比赛是当天12点开始的。
        barrage_start_datetime = datetime.datetime.strptime(barrage_start_datetime_str, "%Y-%m-%d %H:%M:%S")
        sender_name_list = []
        barrages = []
        for line in input_file:
            split_info = line.strip().split("\t")
            if len(split_info) < 3:
                continue
            datetime_str = split_info[0]
            sender_name = split_info[1]
            content = split_info[2]
            barrage_datetime = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            if barrage_datetime < barrage_start_datetime:
                continue  # 比赛还未开始的弹幕略去
            barrage_timestamp = str((barrage_datetime - barrage_start_datetime).total_seconds())
            sender_name_list.append([sender_name])
            # 创建barrage对象
            barrage = Barrage(play_timestamp=barrage_timestamp, sender_id=sender_name, content=content)
            barrages.append(barrage)
        # 为每一个用户的名称对应一个唯一的数字表示
        dictionary = corpora.Dictionary(sender_name_list)
        dictionary.save("live_sender_name.dict")
        # 在将barrages中的barrage用户名称替换为刚刚生成的对应数字表示
        for barrage in barrages:
            barrage.sender_id = str(dictionary.token2id[barrage.sender_id])
        return barrages


if __name__ == "__main__":
    # barrages = get_barrage_from_txt_file("../../data/local/9.txt")
    # file_path = FileUtil.get_word_segment_result_file_path("../../data/local/9.txt")
    # barrage_seg_list = wordseg.segment_barrages(barrages)
    # wordseg.save_segment_barrages(file_path, barrage_seg_list)
    # barrage_seg_list = wordseg.load_segment_barrages(file_path)
    # for barrage_seg in barrage_seg_list:
    #     print str(barrage_seg.play_timestamp), u"\t", u"\t".join([seg.word + u"\t" + seg.flag for seg
    #                                                               in barrage_seg.sentence_seg_list])

    # gen_sorted_barrage_file(os.path.join(FileUtil.get_local_data_dir(), "2171229.txt"))

    parse_barrage_xml_to_txt("4547002.xml")

    # barrages = get_barrage_from_live_text_file(os.path.join(FileUtil.get_project_root_path(), "data", "AlphaGo",
    #                                                         "bilibili", "2016-03-09.txt"))
    # for barrage in barrages:
    #     print barrage.play_timestamp, u"\t", barrage.sender_id, u"\t", barrage.content, u"\n"
