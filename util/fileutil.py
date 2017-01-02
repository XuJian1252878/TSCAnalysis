#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import os

"""
文件存取的操作，将弹幕数据写入本地文件中。
"""

__author__ = "htwxujian@gmail.com"


class FileUtil(object):

    # 如果路径存在，并且是一个文件夹，那么返回true；否则返回false。
    @staticmethod
    def is_dir_exists(dir_path):
        if os.path.isdir(dir_path):
            return True
        else:
            return False

    # 如果路径存在，并且是一个文件，那么返回true；否则返回false。
    @staticmethod
    def is_file_exists(file_path):
        if os.path.isfile(file_path):
            return True
        else:
            return False

    # 如果文件夹不存在，那么创建该文件夹，路径链中的文件夹若不存在也将会一同被创建。
    @staticmethod
    def create_dir_if_not_exist(dir_path):
        if FileUtil.is_dir_exists(dir_path) is False:
            os.makedirs(dir_path)

    # 获得当前脚本的运行目录。
    @staticmethod
    def _get_cur_dir():
        return os.path.dirname(os.path.realpath(__file__))

    # 获得项目的根路径。
    @staticmethod
    def get_project_root_path():
        (project_root_path, util_path) = os.path.split(FileUtil._get_cur_dir())
        return project_root_path

    # 获得项目数据根目录
    @staticmethod
    def get_data_root_dir():
        base_path = FileUtil.get_project_root_path()
        data_root_path = os.path.join(base_path, "data")
        return data_root_path

    # 获得本地数据目录。
    @staticmethod
    def get_local_data_dir():
        base_path = FileUtil.get_project_root_path()
        local_data_path = os.path.join(base_path, "data", "local")
        FileUtil.create_dir_if_not_exist(local_data_path)
        return local_data_path

    # 获得弹幕文件的路径。
    # 参数： is_corpus 当前的弹幕文件是否为语料，默认为false，不为语料
    #       cid 视频对应的cid信息（基于b站）
    @staticmethod
    def get_barrage_file_path(cid, is_corpus=False):
        if not is_corpus:
            return os.path.join(FileUtil.get_local_data_dir(), cid + ".txt")
        else:
            return os.path.join(FileUtil.get_corpus_dir(), cid + ".txt")

    # 分块读取文件的内容。
    @staticmethod
    def __read_file_by_block(input_file, buffer_size=65536):
        while True:
            nb = input_file.read(buffer_size)
            if not nb:
                break
            yield nb

    # 获得当前文件的总行数。
    @staticmethod
    def get_file_line_count(file_path):
        if not FileUtil.is_file_exists(file_path):
            return False
        with open(file_path, "rb") as input_file:
            # 返回一个迭代器，对迭代器中的数据汇总。
            return sum(line.count("\n") for line in FileUtil.__read_file_by_block(input_file))

    # 获得文件最后几行的内容。
    @staticmethod
    def get_file_last_n_line_content(file_path, last_n=5, buffer_size=1024):
        with open(file_path, "rb") as input_file:
            seek_times = 0
            line_count = 0
            # 文件指针首先调到文件末尾。
            input_file.seek(0, 2)
            # 从文件末尾向前seek，统计末尾内容的换行符数量。
            while input_file.tell() > 0 and line_count < (last_n + 1):
                seek_times += 1
                input_file.seek(-seek_times * buffer_size, 2)
                content = input_file.read(seek_times * buffer_size)
                input_file.seek(-seek_times * buffer_size, 2)
                line_count = content.count("\n")
            content = input_file.read(seek_times * buffer_size)
        # 得到文本的最后几行内容。
        last_lines = [line for line in content.split("\n") if line != ""]
        if len(last_lines) > last_n:
            last_lines = last_lines[len(last_lines) - last_n: len(last_lines)]
        for index in xrange(0, len(last_lines)):
            last_lines[index] = last_lines[index].decode("utf-8", "ignore")
        return last_lines

    # 构建分词结果文件的文件名称（根据本地txt弹幕文件的cid 加上
    # -seg-result.json 问分词结果的文件名。即cid-seg-result.json）
    # 参数： cid 本地原始弹幕文件的cid信息。
    @staticmethod
    def get_word_segment_result_file_path(cid):
        word_segment_result_file_path = u"".join([cid, "-seg-result.json"])
        word_segment_result_file_path = os.path.join(FileUtil.get_word_segment_dir(), word_segment_result_file_path)
        return word_segment_result_file_path

    # 获得分词结果的路径。
    @staticmethod
    def get_word_segment_dir():
        project_root_path = FileUtil.get_project_root_path()
        word_segment_dir = os.path.join(project_root_path, "data", "wordsegment")
        FileUtil.create_dir_if_not_exist(word_segment_dir)
        return word_segment_dir

    # 从弹幕的文件路径中获得cid信息
    @staticmethod
    def get_cid_from_barrage_file_path(barrage_file_path):
        (barrage_file_dir, barrage_file_name) = os.path.split(barrage_file_path)
        split_info = barrage_file_name.split(".")
        cid = split_info[0]
        return cid

    # 获得相似度矩阵的结果存储路径
    @staticmethod
    def get_similarity_matrix_dir():
        data_dir = FileUtil.get_data_root_dir()
        similarity_matrix_dir = os.path.join(data_dir, "matrix")
        FileUtil.create_dir_if_not_exist(similarity_matrix_dir)
        return similarity_matrix_dir

    # 获得项目字典数据的存储路径
    @staticmethod
    def get_dict_dir():
        data_dir = FileUtil.get_data_root_dir()
        dict_dir = os.path.join(data_dir, "dict")
        FileUtil.create_dir_if_not_exist(dict_dir)
        return dict_dir

    # 获得tfidf字典数据的路径
    @staticmethod
    def get_train_model_dir():
        data_dir = FileUtil.get_data_root_dir()
        train_model_dir = os.path.join(data_dir, "model")
        FileUtil.create_dir_if_not_exist(train_model_dir)
        return train_model_dir

    # 获得zscore结果的存储路径
    @staticmethod
    def get_zscore_dir():
        data_dir = FileUtil.get_data_root_dir()
        zscore_dir = os.path.join(data_dir, "zscore")
        FileUtil.create_dir_if_not_exist(zscore_dir)
        return zscore_dir

    # 获得情感分析结果的数据路径
    @staticmethod
    def get_emotion_dir():
        data_dir = FileUtil.get_data_root_dir()
        emotion_dir = os.path.join(data_dir, "emotion")
        FileUtil.create_dir_if_not_exist(emotion_dir)
        return emotion_dir

    # 获得语料库的路径
    @staticmethod
    def get_corpus_dir():
        data_dir = FileUtil.get_data_root_dir()
        corpus_dir = os.path.join(data_dir, "corpus")
        FileUtil.create_dir_if_not_exist(corpus_dir)
        return corpus_dir

    # 获得训练数据的目录路径
    @staticmethod
    def get_train_data_dir():
        data_dir = FileUtil.get_data_root_dir()
        train_data_dir = os.path.join(data_dir, "train")
        FileUtil.create_dir_if_not_exist(train_data_dir)
        return train_data_dir

    # 获取测试数据的目录路径
    @staticmethod
    def get_test_data_dir():
        data_dir = FileUtil.get_data_root_dir()
        test_data_dir = os.path.join(data_dir, "test")
        FileUtil.create_dir_if_not_exist(test_data_dir)
        return test_data_dir

    @staticmethod
    def get_dir_files(dir_name):
        file_dir_list = os.listdir(dir_name)
        files = []
        for file_or_dir in file_dir_list:
            file_or_dir_path = os.path.join(dir_name, file_or_dir)
            if os.path.isfile(file_or_dir_path):  # 如果是文件
                files.append(file_or_dir)
        return files


if __name__ == "__main__":
    print FileUtil.get_dir_files(FileUtil.get_train_data_dir())
    # print FileUtil.get_local_data_dir()
