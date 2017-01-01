#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-


"""
将弹幕文件中的每一句弹幕转化成向量信息
"""

from gensim.models import Doc2Vec
import os
import numpy as np
from util.fileutil import FileUtil
import math
from util.loader.dataloader import get_barrage_from_txt_file
from wordsegment.wordseg import segment_barrages
from analysis.model.timewindow import TimeWindow
from analysis.model.kmeans import Kmeans
from analysis.model.dbscan import Dbscan
from gensim import corpora, models

# 这里使用三种方法生成f向量
METHOD_F = 'f'
METHOD_WORD_BASE = 'wordbase'
METHOD_LDA = 'lda'

# lda方法主题的数量
LDA_TOPIC_COUNT = 10


def load_doc2vec_model(model_name):
    """
    返回已经训练好的doc2vec模型
    :param model_name:
    :return:
    """
    model_path = os.path.join(FileUtil.get_train_model_dir(), model_name)
    model = Doc2Vec.load(model_path)
    return model


def get_pure_barrage_words_list(sentence_seg_list):
    """
    返回一条弹幕经过分词处理之后的词语列表
    :param sentence_seg_list:
    :return:
    """
    pure_words_list = []
    for item in sentence_seg_list:
        pure_words_list.append(item.word)
    return pure_words_list


def __justify_time_window_barrage_empty(time_window):
    """
    判断一个时间窗口内的弹幕信息是否为空
    :param time_window:
    :return:
    """
    if len(time_window.barrage_seg_list) <= 0:
        # 时间窗口内没有弹幕，那么没有采取的价值，将会被过滤
        time_window.f = None
        time_window.rating = None
        return True
    return False


def gen_f_vector_time_window(time_window_list, cluster):
    """
    获取每个时间窗口内的f向量
    :param time_window_list:
    :param cluster:
    :return:
    """
    for time_window in time_window_list:
        f = np.zeros(len(cluster))
        if __justify_time_window_barrage_empty(time_window):
            # 时间窗口内没有弹幕，那么没有采取的价值，将会被过滤
            continue
        for barrage_seg in time_window.barrage_seg_list:
            index = barrage_seg.index
            for topic_no, barrage_index_list in cluster.items():
                if index in barrage_index_list:
                    f[topic_no] += 1  # 记录这个时间窗口的弹幕在各个主题下的数量
                    break
        time_window.f = f


def gen_lda_vector_time_window(time_window_list, dictionary, lda_model):
    """
    对于每一个time_window 生成这个时间窗口内弹幕的主题分布信息
    :param time_window_list: 其中的time_window 已经填充了 barrage_seg_list
    :param dictionary:
    :param lda_model:
    :return:
    """
    for time_window in time_window_list:
        if __justify_time_window_barrage_empty(time_window):
            # 时间窗口内没有弹幕，那么没有采取的价值，将会被过滤
            continue
        barrage_segs = []  # 这个时间窗口内的弹幕词语列表
        for barrage_seg in time_window.barrage_seg_list:
            barrage_segs += get_pure_barrage_words_list(barrage_seg.sentence_seg_list)
        barrage_bow = dictionary.doc2bow(barrage_segs)
        barrage_lda = lda_model[barrage_bow]

        barrage_lda_vector = np.zeros(LDA_TOPIC_COUNT)
        for topic_no, percent in barrage_lda:
            barrage_lda_vector[topic_no] = percent
        time_window.f = barrage_lda_vector


def gen_wordbase_vector_time_window(time_window_list, dictionary):
    """
    获取每一个时间窗口下弹幕的词频向量信息
    :param time_window_list:
    :param dictionary:
    :return:
    """
    corpus_words_count = len(dictionary.keys())
    for time_window in time_window_list:
        if __justify_time_window_barrage_empty(time_window):
            # 时间窗口内没有弹幕，那么没有采取的价值，将会被过滤
            continue
        barrage_segs = []  # 这个时间窗口内的弹幕词语列表
        for barrage_seg in time_window.barrage_seg_list:
            barrage_segs += get_pure_barrage_words_list(barrage_seg.sentence_seg_list)
        barrage_bow = dictionary.doc2bow(barrage_segs)
        wordbase_vector = np.zeros(corpus_words_count)
        for token_id, word_fre in barrage_bow:
            wordbase_vector[token_id] = word_fre  # 记录词频向量信息
        time_window.f = wordbase_vector


def train_barrage(barrage_seg_list):
    """
    根据弹幕文件的内容获取 每个时间窗口之内的f向量
    :param barrage_seg_list:
    :return:
    """
    # 获取训练的 doc2vec 来训练 分词后的弹幕文件
    doc2vec_model = load_doc2vec_model('d2v.txt')

    # 由doc2vec获得整条弹幕的向量信息
    barrage_vector = []
    for item in barrage_seg_list:
        pure_vector = get_pure_barrage_words_list(item.sentence_seg_list)
        inferred_vector = doc2vec_model.infer_vector(pure_vector)
        barrage_vector.append(inferred_vector)

    barrage_vector = np.array(barrage_vector)
    return barrage_vector


def cluster_barrage_vector(barrage_vector, cluster_num=10):
    """
    对获得的弹幕语句进行聚类
    :param barrage_vector:
    :param cluster_num:
    :return:
    """
    center_points, cluster = Kmeans(clusters_num=cluster_num, x_features=barrage_vector).cluster()
    # cluster, noises = Dbscan(x_features=barrage_vector).fit()
    return cluster


def get_highlight(barrage_seg_list, cid, method=METHOD_F, is_train=False, train_sample=None, f_cluster=None):
    """
    根据每一条弹幕的分词列表以及聚类信息，获取电影中主题较为集中的片段
    :param barrage_seg_list:
    :param cid
    :param method
    :param is_train 训练 和 测试 情况下load的time_window不一样
    :param train_sample 人工标注的数据
    :param f_cluster 聚好类的弹幕数据
    :return:
    """
    # 以十秒为时间窗口来划分弹幕文件
    if is_train:
        # 获取人工标注数据对应的时间窗口文件
        time_window_list = TimeWindow.gen_train_time_window(train_sample, barrage_seg_list, cid)
    else:
        # 获取弹幕数据的全部时间窗口信息
        time_window_list = TimeWindow.gen_time_window_barrage_info(barrage_seg_list, cid)
    # 获得每个时间窗口内的f向量
    if method == METHOD_F:
        # 对获得的弹幕进行聚类
        # barrage_vector = train_barrage(barrage_seg_list)
        # cluster = cluster_barrage_vector(barrage_vector)
        gen_f_vector_time_window(time_window_list, f_cluster)
    elif method == METHOD_WORD_BASE:
        # 获取弹幕的词频向量信息
        dictionary = corpora.Dictionary.load(os.path.join(FileUtil.get_train_model_dir(),
                                                          str(cid) + "-barrage-words.dict"))
        gen_wordbase_vector_time_window(time_window_list, dictionary)
    elif method == METHOD_LDA:
        # 获取弹幕的lda向量
        dictionary = corpora.Dictionary.load(os.path.join(FileUtil.get_train_model_dir(),
                                                          str(cid) + "-barrage-words.dict"))
        lda_model = models.LdaModel.load(os.path.join(FileUtil.get_train_model_dir(), str(cid) + "-barrage-lda.model"))
        gen_lda_vector_time_window(time_window_list, dictionary, lda_model)

    if not is_train:
        # 因为有人在开始和结束的时候刷屏，所以把开始和结束的一分钟之内的弹幕去掉
        if len(time_window_list) > 180:  # 如果视频片段大于30分钟
            time_window_list = time_window_list[6: -6]
        # 计算每个时间窗口的rating值
        max_rating, min_rating = rating_f(time_window_list)
        # 去除主题不集中的时间窗口
        time_window_list = filter_time_window(time_window_list, max_rating, min_rating)
    return time_window_list


def rating_f(time_window_list):
    """
    计算rating的值，以及返回最大和最小的rating值
    :param time_window_list:
    :return:
    """
    ratings = []
    for time_window in time_window_list:
        if time_window.f is None:
            continue  # 该时间窗口没有弹幕信息，直接跳过
        k = len(time_window.f)
        f_mean = np.mean(time_window.f)
        rating_up = 0
        for item in time_window.f:
            rating_up += ((item - f_mean) ** 2)

        rating_up /= (k * 1.0)
        print time_window.f
        p = time_window.f * 1.0 / time_window.f.sum(axis=0)
        entropy = 1  # 避免只有一个主题有弹幕，然后entropy被算为0
        for item in p:
            if item > 0:
                entropy += (-item) * math.log(item)

        time_window.rating = rating_up * 1.0 / entropy
        ratings.append(rating_up * 1.0 / entropy)
    return max(ratings), min(ratings)


def filter_time_window(time_window_list, max_rating, min_rating):
    """
    返回rating值大于阈值的时间窗口
    :param time_window_list:
    :param max_rating:
    :param min_rating:
    :return:
    """
    threshold = 0.7 * min_rating + 0.3 * max_rating
    time_window_result = []
    for time_window in time_window_list:
        if time_window.rating > threshold:
            time_window_result.append(time_window)
    return time_window_result


def highlight_window_main(barrage_file, method=METHOD_F):
    """
    根据弹幕文件，获取 主题 较为集中的视频片段信息
    :param barrage_file:
    :param method:
    :return:
    """
    # 将弹幕文件中的每条弹幕信息化成向量
    barrages = get_barrage_from_txt_file(barrage_file)
    cid = FileUtil.get_cid_from_barrage_file_path(barrage_file)
    barrage_seg_list = segment_barrages(barrages, cid)
    # barrage_vector = train_barrage(barrage_seg_list)

    # 获取highlight的视频片段信息（起始位置）
    highlight_window_list = get_highlight(barrage_seg_list, cid, method)
    return highlight_window_list


if __name__ == '__main__':
    barrage_file_path = '../../data/local/9.txt'
    save_corpus_path = '../../data/local/corpus-words.txt'
    # barrages = get_barrage_from_txt_file(barrage_file_path)
    # cid = FileUtil.get_cid_from_barrage_file_path(barrage_file_path)
    # barrage_seg_list = segment_barrages(barrages, cid)

    # train_barrage(barrage_file_path, METHOD_LDA)

    # 接口使用示例
    print highlight_window_main(barrage_file_path, METHOD_WORD_BASE)

