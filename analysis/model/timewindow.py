#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import codecs
import logging
import os
import math
import numpy as np

import util.loader.dataloader as dataloader
import wordsegment.wordseg as wordseg
from util.datetimeutil import DateTimeUtil
from util.fileutil import FileUtil

"""
记录每个时间窗口内的弹幕分词结果，以及时间窗口划分的配置信息。
"""


class TimeWindow(object):

    __TIME_WINDOW_SIZE = 10  # 时间窗口的大小，以秒为单位
    __SLIDE_TIME_INTERVAL = 10  # 以10s为时间间隔滑动，创建时间窗口，以秒为单位

    def __init__(self, cid, time_window_index, start_timestamp, end_timestamp):
        self.cid = cid
        self.time_window_index = time_window_index
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.barrage_count = 0  # 该时间窗口内弹幕的数量
        self.valid_barrage_word_count = 0  # 该时间窗口内弹幕词语的数量
        self.barrage_seg_list = []  # 该时间窗口内对应的弹幕分词列表
        self.f = []  # 该时间窗口对应的f向量
        self.rating = 0  # 该时间窗口对应的rating值
        self.label = None  # 如果是训练数据的话，还会填充label信息
        self.predict_label = None  # 预测的时间窗口 标签

    @classmethod
    def get_time_window_size(cls):
        return cls.__TIME_WINDOW_SIZE

    @classmethod
    def get_slide_time_interval(cls):
        return cls.__SLIDE_TIME_INTERVAL

    # 将时间窗口的下标、开始结束时间戳、弹幕数量、有用词数量保存入文件中，便于今后的zscore分析
    @classmethod
    def __save_time_window_info_to_file(cls, cid, time_window_list):
        file_path = os.path.join(FileUtil.get_zscore_dir(), str(cid) + "-time-window-info.txt")
        with codecs.open(file_path, "wb", "utf-8") as output_file:
            for time_window in time_window_list:
                time_window_info = unicode(str(time_window.time_window_index)) + u"\t" \
                                   + DateTimeUtil.format_barrage_play_timestamp(time_window.start_timestamp) + u"\t" \
                                   + DateTimeUtil.format_barrage_play_timestamp(time_window.end_timestamp) + u"\t" \
                                   + unicode(str(time_window.barrage_count)) + u"\t" \
                                   + unicode(str(time_window.valid_barrage_word_count)) + u"\n"
                output_file.write(time_window_info)

    # 将弹幕的信息按照时间窗口分类
    # 参数：barrage_seg_list 一个已经排好序的，已经切好词的barrage_seg_list列表，或者是原始的未切词的弹幕列表（已排好序）。
    # 返回一个 TimeWindow 列表。
    @classmethod
    def gen_time_window_barrage_info(cls, barrage_seg_list, cid):
        time_window_index = 0
        start_timestamp = 0
        end_timestamp = start_timestamp + cls.__TIME_WINDOW_SIZE
        time_window_list = []
        while start_timestamp <= barrage_seg_list[-1].play_timestamp:
            temp_seg_list = []
            valid_barrage_word_count = 0
            for barrage_seg in barrage_seg_list:
                if (start_timestamp <= barrage_seg.play_timestamp) and (end_timestamp > barrage_seg.play_timestamp):
                    temp_seg_list.append(barrage_seg)
                    valid_barrage_word_count += len(barrage_seg.sentence_seg_list)
                elif end_timestamp <= barrage_seg.play_timestamp:
                    break
            logging.info(u"建立第 " + str(time_window_index) + u" 个时间窗口！！")
            # 产生一个新的timewindow对象
            time_window = TimeWindow(cid, time_window_index, start_timestamp, end_timestamp)
            time_window.barrage_seg_list = temp_seg_list
            time_window.barrage_count = len(temp_seg_list)  # 记录该时间窗口下的弹幕数量
            time_window.valid_barrage_word_count = valid_barrage_word_count  # 记录该时间窗口下有效的弹幕词语的数量
            time_window_list.append(time_window)

            start_timestamp += cls.__SLIDE_TIME_INTERVAL
            end_timestamp = start_timestamp + cls.__TIME_WINDOW_SIZE
            time_window_index += 1
        # 将时间窗口的相关数据信息写入zscore文件中
        cls.__save_time_window_info_to_file(cid, time_window_list)
        return time_window_list

    @staticmethod
    def gen_train_time_window(train_sample, barrage_seg_list, cid):
        """
        根据训练数据list[tuple(start_time, end_time, label)] 来生成指定时间范围内的时间窗口
        :param train_sample:
        :return:
        """
        time_window_list = []
        for start_seconds, end_seconds, label in train_sample:

            start = start_seconds
            end = start_seconds + TimeWindow.__TIME_WINDOW_SIZE

            while start < end_seconds:
                temp_seg_list = []
                for barrage_seg in barrage_seg_list:
                    if start <= barrage_seg.play_timestamp <= end:
                        temp_seg_list.append(barrage_seg)
                time_window = TimeWindow(cid, start / TimeWindow.__TIME_WINDOW_SIZE, start, end)
                time_window.barrage_seg_list = temp_seg_list
                time_window.label = label
                time_window_list.append(time_window)

                # 更新开始以及结束时间
                start = end
                end = start + TimeWindow.__TIME_WINDOW_SIZE
        return time_window_list

# if __name__ == "__main__":
#     barrage_file_path = "../../data/local/4547002.txt"
#     # "../../data/local/9.txt" "../../data/AlphaGo/bilibili/2016-03-09.txt" "../../data/local/2065063.txt"
#     barrages = dataloader.get_barrage_from_txt_file(barrage_file_path)
#     # barrages = dataloader.get_barrage_from_live_text_file(barrage_file_path)



    # cid = FileUtil.get_cid_from_barrage_file_path(barrage_file_path)
    # barrage_seg_list = wordseg.segment_barrages(barrages, cid)
    # time_window_list = TimeWindow.gen_time_window_barrage_info(barrage_seg_list)
    # for time_window in time_window_list:
    #     str_info = ''
    #     for barrage_seg in time_window.barrage_or_seg_list:
    #         for sentence_seg in barrage_seg.sentence_seg_list:
    #             str_info += (sentence_seg.word + sentence_seg.flag + u"\t")
    #     print str(time_window.time_window_index), u"\t", str(time_window.start_timestamp), u"\t",\
    #         str(time_window.end_timestamp), u"\t", str_info



    # time_window_list = TimeWindow.gen_user_word_frequency_by_time_window(barrage_seg_list)
    # with codecs.open(FileUtil.get_word_segment_result_file_path(cid), "wb", "utf-8") as output_file:
    #     for time_window in time_window_list:
    #         str_info = str(time_window.time_window_index) + u"\t"
    #         for user_id, word_frequency in time_window.user_word_frequency_dict.items():
    #             str_info += (user_id + u"\t")
    #             for word, frequency in word_frequency.items():
    #                 str_info += (word + u"\t" + str(frequency) + u"\t")
    #         print str_info
    #         output_file.write(str_info + u"\n")

    # time_window_list = TimeWindow.gen_user_word_frequency_by_time_window(barrage_seg_list, cid)
    # SimMatrix.gen_jaccard_sim_matrix_by_word_frequency(time_window_list)

    # time_window_list = TimeWindow.gen_user_token_tfidf_by_time_window(barrage_seg_list, cid)
    # SimMatrix.gen_cosine_sim_matrix(time_window_list, 2)

    # time_window_list = TimeWindow.gen_user_topic_lda_by_time_window(barrage_seg_list, cid)
    # SimMatrix.gen_cosine_sim_matrix(time_window_list, 3)
