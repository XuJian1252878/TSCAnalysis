#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from sklearn import svm
import codecs
from util.fileutil import FileUtil
import os
from util.loader.dataloader import get_barrage_from_txt_file
from wordsegment.wordseg import segment_barrages
from analysis.model.timewindow import TimeWindow
from analysis.model.embedded import cluster_barrage_vector, gen_f_vector_time_window, train_barrage
from analysis.model.embedded import METHOD_LDA, METHOD_WORD_BASE, METHOD_F, get_highlight


def __covert_time(time_str):
    """
    将MM:DD格式的时间转化为秒数
    :param time_str:
    :return:
    """
    infos = time_str.split(':')
    if len(infos) < 2:
        Exception('日期格式有误！！' + time_str)
        return
    seconds = int(infos[0]) * 60 + int(infos[1])
    return seconds


def __load_train_or_data(train_data_filename):
    """
    读取人工标注的训练数据的信息，人工标注的格式为 每一行：MM:DD\tMM:DD\tlabel\n
    :param train_data_filename:
    :return:
        train_samples: list[tuple(start_time, end_time)]
    """
    with codecs.open(train_data_filename, 'rb', 'utf-8') as input_file:
        train_samples = []
        for line in input_file:
            line = line.strip().split('\t')
            if len(line) < 3:
                continue
            start_time = __covert_time(line[0])
            end_time = __covert_time(line[1])
            train_samples.append((start_time, end_time, line[2]))

        # 按照开始时间对训练数据进行排序
        train_samples = sorted(train_samples, key=lambda item: item[0])
        return train_samples


def __save_train_or_test_data(test_data_file, result_highlight):
    """
    将预测的结果信息存入本地文件中
    :param test_data_file:
    :param result_highlight:
    :return:
    """
    with codecs.open(test_data_file, 'wb', 'utf-8') as output_file:
        for item in result_highlight:
            minute_str = unicode(str(item[0] / 60)) + u':' + unicode(str(item[0] % 60))
            second_str = unicode(str(item[1] / 60)) + u':' + unicode(str(item[1] % 60))
            label = item[2]
            info = u'\t'.join([minute_str, second_str, label]) + u'\n'
            output_file.write(info)


def match_train_sample_to_time_window(barrage_seg_list, train_sample, cid, method=METHOD_F):
    """
    将测试数据对应的time_window找出来，并且计算每一个time_window的f向量信息
    :param barrage_seg_list:
    :param train_sample:
    :param cid:
    :param method:
    :return:
    """
    time_window_list = get_highlight(barrage_seg_list, cid, method, True, train_sample)
    return time_window_list


def __gen_features_and_labels(time_window_list):
    """
    将time_window_list中的属性和标签信息集中读取出来
    :param time_window_list:
    :return:
    """
    # 获取训练属性以及训练标签列表
    x_features = []
    y_labels = []
    for time_window in time_window_list:
        x_features.append(time_window.f)
        y_labels.append(time_window.label)
    return x_features, y_labels


def train_svm(time_window_list):
    """
    根据时间窗口信息获取svm需要的 训练属性列表 以及 训练标签列表
    :param time_window_list:
    :return:
    """
    # 获取训练属性以及训练标签列表
    x_features, y_labels = __gen_features_and_labels(time_window_list)

    # 训练svm模型
    svm_model = svm.SVC()
    svm_model.fit(x_features, y_labels)
    return svm_model


def svm_predict(svm_model, highlight_window_list, method=METHOD_F):
    """
    根据训练好的svm模型，
    :param svm_model:
    :param highlight_window_list:
    :param method:
    :return:
    """
    # 获取time_window 向量属性的列表
    x_features, y_labels = __gen_features_and_labels(highlight_window_list)
    predict_labels = svm_model.predict(x_features)

    print predict_labels
    # 填充 time_window 的 predict_label
    for index in range(len(highlight_window_list)):
        time_window = highlight_window_list[index]
        time_window.predict_label = predict_labels[index]
    return highlight_window_list


def merge_highlight_by_same_label(highlight_window_list, cid):
    """
    将具有相同predict_label的time_window标记成一个片段
    :param highlight_window_list:
    :param cid:
    :return:
        highlight_slices: list[tuple(start, end, label)]  这里的start end以秒的方式来表示
    """
    result_highlight = []

    highlight_length = len(highlight_window_list)

    for index in range(highlight_length):
        time_window = highlight_window_list[index]

        start_flag = time_window.start_timestamp
        end_flag = time_window.end_timestamp

        cur_label = time_window.predict_label
        cur_window_index = time_window.time_window_index  # 当前时间窗口在原弹幕文件中的下标

        # 开始寻找时间上相连的，并且标签相同的片段
        back_window_index = cur_window_index
        forward_index = index + 1
        while forward_index < highlight_length:
            forward_window = highlight_window_list[forward_index]
            forward_label = forward_window.predict_label

            # 向前时间窗口在原弹幕文件中的下标
            forward_window_index = forward_window.time_window_index

            # 两个时间窗口在时间上相连，标签类型又相同，那么这两个标签可以相连
            if back_window_index + 1 == forward_window_index and forward_label == cur_label:
                forward_index += 1
                back_window_index = forward_window_index
                end_flag = forward_window.end_timestamp
            else:
                break

        result_highlight.append((start_flag, end_flag, cur_label))
        # 调整一下当前的下标
        index = forward_index - 1

    # 存储当前的highlight列表信息
    __save_train_or_test_data(os.path.join(FileUtil.get_test_data_dir(), cid + '_predict_result.txt'), result_highlight)
    return result_highlight


def __calc_seconds_and_labels(highlight_slice):
    """
    计算一个highlight片段里面的总秒数，以及总共的label数量
    :param highlight_slice:
    :return:
    """
    seconds = 0
    labels = set([])
    for start, end, label in highlight_slice:
        seconds += (end - start)
        labels.add(label)
    label_count = len(labels)
    return seconds, label_count


def evaluate_effect(baseline_file, predict_file):
    """
    将预测出的结果跟baseline（原来人工标好标签的字段），重叠时间的P R F1，label的P R F1
    :param baseline_file:
    :param predict_file:
    :return:
    """
    baseline_sample = __load_train_or_data(baseline_file)
    predict_result = __load_train_or_data(predict_file)

    seconds_baseline, labels_baseline = __calc_seconds_and_labels(baseline_sample)
    seconds_predict, labels_predict = __calc_seconds_and_labels(predict_result)

    # 首先寻找重叠时间
    overlape_seconds = 0
    overlape_labels_set = set([])
    overlape_labels = 0
    for start_p, end_p, label_p in predict_result:
        for start_b, end_b, label_b in baseline_sample:
            if start_p > end_b or end_p < start_b:
                # 没有任何重叠
                continue
            else:
                # 有重叠的情况
                start = max([start_b, start_p])
                end = min([end_b, end_p])
                overlape_seconds += end - start
                if label_p == label_b:
                    overlape_labels_set.add(label_b)
    overlape_labels = len(overlape_labels_set)

    # 计算重叠时间的指标信息
    precision = overlape_seconds * 1.0 / seconds_predict
    recall = overlape_seconds * 1.0 / seconds_baseline
    F1 = (2.0 * precision * recall) / (precision + recall)

    # 计算重叠标签的指标信息
    precision_label = overlape_labels * 1.0 / labels_predict
    recall_label = overlape_labels * 1.0 / labels_baseline
    F1_label = (2.0 * precision_label * recall_label) / (precision_label + recall_label)

    return precision, recall, F1, precision_label, recall_label, F1_label


def main(barrage_file, method=METHOD_F):
    """
    svm聚类的主流程函数
    :param barrage_file:
    :param method:
    :return:
    """
    # 首先读取train数据对应的弹幕文件信息
    barrages = get_barrage_from_txt_file(barrage_file)
    cid = FileUtil.get_cid_from_barrage_file_path(barrage_file)
    barrage_seg_list = segment_barrages(barrages, cid)

    # 然后读取人工标注的 barrage file的电影片段label信息
    train_sample = __load_train_or_data(os.path.join(FileUtil.get_train_data_dir(), cid + '_train_data.txt'))

    # 匹配训练数据以及其对应的时间窗口信息
    time_window_list = match_train_sample_to_time_window(barrage_seg_list, train_sample, cid, method)

    # 训练svm模型
    svm_model = train_svm(time_window_list)

    # 获取相应的time_window信息，读取全部的弹幕数据
    highlight_window_list = get_highlight(barrage_seg_list, cid, method)

    # 获取标记标签后的highlight信息
    highlight_window_list = svm_predict(svm_model, highlight_window_list, method)

    # 合并时间相连的并且标签相同的 high_light
    result_highlight = merge_highlight_by_same_label(highlight_window_list, cid)

    # 计算结果预测的指标信息
    baseline_file = os.path.join(FileUtil.get_train_data_dir(), cid + '_train_data.txt')
    predict_file = os.path.join(FileUtil.get_test_data_dir(), cid + '_predict_result.txt')
    precision, recall, F1, precision_label, recall_label, F1_label = evaluate_effect(baseline_file, predict_file)
    return precision, recall, F1, precision_label, recall_label, F1_label


if __name__ == '__main__':
    barrage_file_path = '../../data/local/2065063.txt'
    save_corpus_path = '../../data/local/8752370-save.txt'

    main(barrage_file_path)



