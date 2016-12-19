#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import numpy as np
import random
import math


class Kmeans(object):

    def __init__(self, clusters_num, x_features, file_path=None, y_labels=None):
        self.clusters_num = clusters_num  # 划分的集群的个数
        self.file_path = file_path  # 数据文件的路径
        # x_features, y_labels = read_data(flag=0)
        self.x_features_train = self.normalize_feature(x_features)  # 训练数据属性
        self.y_labels_train = y_labels  # 训练数据标签

        self.train_clusters = {}  # 训练集簇
        self.center_points = []  # 记录下训练得到的中心节点信息

    @staticmethod
    def normalize_feature(x_features):
        """
        使样本的每一维数据归一化，样本的每一维属性范围不同，可能会加剧聚类的误差。
        标准化后，特征具有单位方差并以均值为零中心分布。
        :param x_features:
        :return:
        """
        x_features_std = np.copy(x_features)
        row, col = x_features_std.shape
        for col_index in range(col):
            x_features_std[:, col_index] = (x_features[:, col_index] - x_features[:, col_index].mean()) / x_features[:, col_index].std()
        return x_features_std

    @staticmethod
    def calc_distance(vector_1, vector_2):
        """
        计算两个向量之间的欧式距离
        :param vector_1:
        :param vector_2:
        :return:
        """
        distance = np.linalg.norm(vector_1 - vector_2)
        return distance

    def generate_random_center_point(self):
        """
        随机挑选聚类个数的节点的初始化中心节点
        :return:
        """
        point_num = self.x_features_train.shape[0]
        if point_num < self.clusters_num:
            Exception('数据点数量小于数据个数！！')
            return

        random_center_points_index = []
        random_center_points = []
        while len(random_center_points_index) < self.clusters_num:
            random_index = random.randint(a=0, b=point_num - 1)
            if random_index not in random_center_points_index:
                random_center_points.append(self.x_features_train[random_index])
                random_center_points_index.append(random_index)

        return random_center_points

    def __calc_sse(self, center_point, point_index_list):
        """
        计算当前聚类中的点与其中心点的sse距离
        :param center_point: 中心点向量
        :param point_index_list: 中心点对应的簇的训练集点的下标的集合
        :return:
        """
        sse = 0
        for index in point_index_list:
            sse += (self.calc_distance(center_point, self.x_features_train[index]) ** 2)
        return sse

    def __generate_center_point(self, point_index_list):
        """
        在大致得到一个聚类的点之后，重新计算他们的中心点位置
        :param point_index_list: 一个聚类中的点对应在原数据中的下标
        :return:
        """
        count = len(point_index_list)

        count_vector = np.zeros(self.x_features_train[0].shape)
        for index in point_index_list:
            count_vector += self.x_features_train[index]
        center_point = count_vector * 1.0 / count
        sse = self.__calc_sse(center_point, point_index_list)
        return center_point, sse

    @staticmethod
    def __init_cluster(center_points):
        """
        初始化聚类信息
        :return:
        """
        clusters_num = len(center_points)
        clusters = {}
        for index in range(clusters_num):
            clusters[index] = []
        return clusters

    @staticmethod
    def __generate_clusters(center_points, x_features):
        """
        根据中心点生成中心点对应的集群
        :param center_points: 中心点信息
        :param x_features: 待聚类的点的信息
        :return:
        """
        clusters = Kmeans.__init_cluster(center_points)
        for item_index in range(0, len(x_features)):
            item = x_features[item_index]

            min_dist = float('inf')  # 设置初始值为无穷大
            target_index = 0
            for index in range(0, len(center_points)):  # 计算当前点与中心点之间的距离
                # 当前点选择与自己最近的中心点，归入这个中心点的簇中
                dist = Kmeans.calc_distance(item, center_points[index])
                if dist < min_dist:
                    min_dist = dist
                    target_index = index
            # 将item归位到自己的簇中
            if target_index in clusters.keys():
                clusters[target_index].append(item_index)
            else:
                clusters[target_index] = [item_index]
        return clusters

    def __cluster_internal(self, center_points, sse_init, sse_threshold):
        """
        通过递归的方式寻找数据点中合适的集群，以及合适的中心点
        :param center_points:  当前的中心点坐标信息
        :param sse_init:  上一次聚类划分中各集群sse的值
        :param sse_threshold:  两次集群划分中sse的差值小于此值的时候认为集群分类成功
        :return:
        """
        # 根据中心点获得他们对应的聚类信息
        clusters = self.__generate_clusters(center_points, self.x_features_train)

        cluster_sse = []
        # 按照当前的中心点分好簇之后，重新计算中心点以及sse距离
        for cluster_index, cluster_ele in clusters.items():
            point, sse = self.__generate_center_point(cluster_ele)
            center_points[cluster_index] = point  # 更新中心点信息
            cluster_sse.append(sse)

        # 如果上次聚类和这次聚类的sse差值小于阈值，那么kmeans模型生成完成
        print sum(cluster_sse), sse_init, abs(sum(cluster_sse) - sse_init)
        if abs(sum(cluster_sse) - sse_init) < sse_threshold:
            return center_points, clusters  # 返回聚类的中心点，以及中心点对应的簇点信息
        else:
            sse_init = sum(cluster_sse)
            return self.__cluster_internal(center_points, sse_init, sse_threshold)

    def cluster(self):
        """
        对训练数据进行训练，获得训练集的中心点以及各个中心点对应的集群
        :return:
        """
        center_points = self.generate_random_center_point()
        sse_threshold = 0.0001  # 当两次的选取中心点的过程中sse差值不小于它的时候，聚类完成
        sse_init = float('inf')  # sse的初始值

        print u'-----------------------------开始使用训练数据训练kmeans模型--------------------------------------'
        center_points, clusters = self.__cluster_internal(center_points, sse_init, sse_threshold)
        print u'-----------------------------kmeans模型训练完成--------------------------------------'

        self.center_points = center_points
        print u'聚类中点信息：', center_points
        self.train_clusters = clusters

        print u'-----------------------------训练集训练情况--------------------------------------'
        self.justify_effect(clusters, self.y_labels_train)
        print u'-------------------------------------------------------------------------------'
        return center_points, clusters

    @staticmethod
    def justify_effect(clusters, y_labels):
        """
        在控制台打出聚类的准确率等信息，我们将使用 Jaccard系数 FM指数 Rand指数这三个外部指标来衡量聚类的效果
        :param clusters: 当前的聚类信息
        :param y_labels: clusters中的每一个点对应的实际分类
        :return:
        """
        if y_labels is None:
            return

        SS = SD = DS = DD = 0
        for index_1 in range(0, len(y_labels)):
            for index_2 in range(0, len(y_labels)):
                if index_2 <= index_1:
                    continue
                if y_labels[index_1] == y_labels[index_2]:  # 在参考模型中属于同一类
                    flag = False
                    for key, value in clusters.items():
                        if index_1 in value and index_2 in value:  # 在划分的簇中也属于同一类
                            SS += 1
                            flag = True
                            continue
                    if not flag:  # 在划分的簇中不属于同一类
                        DS += 1
                else:  # 在参考的模型中不属于同一类
                    flag = False
                    for key, value in clusters.items():
                        if index_1 in value and index_2 in value:  # 在划分出的簇中属于同一类
                            SD += 1
                            flag = True
                            continue
                    if not flag:  # 在划分的簇中不属于同一类
                        DD += 1
        # 开始计算三个衡量系数的值
        jaccard = SS * 1.0 / (SS + SD + DS)
        fmi = math.sqrt(((SS * 1.0 / (SS + SD)) * (SS * 1.0 / (SS + DS))))
        ri = 2 * (SS + DD) * 1.0 / (len(y_labels) * (len(y_labels) - 1))

        print u'-----------------------------聚类性能度量外部指标--------------------------------------'
        print u'Jaccard系数：', jaccard
        print u'FMI系数：', fmi
        print u'RI系数：', ri
        return jaccard, fmi, ri


if __name__ == '__main__':
    k = Kmeans(4)
    k.cluster()