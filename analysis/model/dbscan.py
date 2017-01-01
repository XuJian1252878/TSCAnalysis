#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import numpy as np
import math
import codecs
import datetime
import os
import pandas as pd
import sklearn
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
from sklearn.neighbors import NearestNeighbors


UNVISITED = False
VISITED = True

UNCLASSIFIED = -2
NOISE = -1


class Dbscan(object):

    def __init__(self, x_features, eps=None, min_pts=None):
        self.x_features_train = x_features  # 训练数据属性
        self.train_clusters = {}  # 训练集簇
        self.k_th = 4

        if (eps is None) and (min_pts is None):
            self.estimate_eps()  # 估计Eps的取值
            self.estimate_min_pts()  # 估计min_pts的取值
        elif (eps is not None) and (min_pts is not None):
            self.eps = eps  # Eps的邻域
            self.min_pts = min_pts  # 以点P为中心、半径为Eps的邻域内的点的个数不少于MinPts，那么p为核心点信息
        else:
            self.eps = 4
            self.min_pts = 4

        self.classifications = []  # 存储聚类的结果
        self.visit = []  # 记录点有没有被遍历

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

    @staticmethod
    def fit_line(distances):
        y = np.array(distances)
        x = np.zeros(y.shape[0])
        for index in range(len(x)):
            x[index] = index
        cof = np.polyfit(x, y, 4)  # 调用函数，用 4 次多项式拟合
        # 返回多项式的系数
        # p = np.poly1d(cof)
        # plt.plot(x, y, 'o', x, p(x), lw=2)
        return cof

    @staticmethod
    def get_target_eps(k_distances):
        """
        在各个点的k_distance列表中，找出位于拐点的k_distance作为eps
        :param k_distances:
        :return:
        """
        cof = Dbscan.fit_line(k_distances)
        # 开始求4次多项式的二阶导 ｆ（ｘ）″＝ １２ａｘ２＋６ｂｘ＋２ｃ
        a = cof[0]
        b = cof[1]
        c = cof[2]
        d = cof[3]
        e = cof[4]

        # 求解该曲线的拐点
        x0 = (-6 * b + math.sqrt(36 * (b ** 2) - 96 * a * c)) * 1.0 / (24 * a)
        target_distance = k_distances[int(x0)]
        return target_distance

    def estimate_eps(self):
        """
        计算每一个点与其他各点的距离，从大到小排序后，选取第4大的距离为k_distance，
        再取各个点的k_distance，并将他们排序，选取变化率最大的距离为eps
        :return:
        """
        k_distances = []
        for target_index in range(len(self.x_features_train)):
            tmp_k_distances = []
            for index in range(len(self.x_features_train)):
                if target_index == index:
                    continue
                vector_1 = self.x_features_train[target_index]
                vector_2 = self.x_features_train[index]
                dist = self.calc_distance(vector_1, vector_2)
                tmp_k_distances.append(dist)
            tmp_k_distances = sorted(tmp_k_distances, key=lambda item: item)
            k_distance = tmp_k_distances[self.k_th - 1]
            k_distances.append(k_distance)
            print 'dbscan k-distance: ', str(k_distance)
        k_distances = sorted(k_distances, key=lambda item: item)

        self.eps = Dbscan.get_target_eps(k_distances)
        return self.eps

    def estimate_min_pts(self):
        """
        在得到估计的eps之后，根据eps获取min_pts的估计值
        :return:
        """
        p_count = 0  # 存储各点在eps距离内的点的数量
        n = len(self.x_features_train)
        for index_1 in range(n):
            sub_p_count = 0
            for index_2 in range(n):
                if index_1 == index_2:
                    continue
                vector_1 = self.x_features_train[index_1]
                vector_2 = self.x_features_train[index_2]
                dist = Dbscan.calc_distance(vector_2, vector_1)
                if dist < self.eps:
                    sub_p_count += 1
            p_count += sub_p_count

        self.min_pts = p_count * 1.0 / n
        return self.min_pts

    def __query_neighbours(self, feature_index, nbrs_indices):
        """
        寻找在feature index的点周围距离在eps之内的点的信息，以feature的下标的形式返回
        :param feature_index:
        :param nbrs_indices:
        :return:
        """
        # neighbours = []
        # x_feature = self.x_features_train[feature_index]
        # for index in range(len(self.x_features_train)):
        #     if index == feature_index:
        #         continue
        #     tmp_x_feature = self.x_features_train[index]
        #     dist = Dbscan.calc_distance(x_feature, tmp_x_feature)
        #     if dist < self.eps:  # 如果该点与原点的距离小于eps，那么认为是邻居
        #         neighbours.append(index)
        # return neighbours

        target_indices = nbrs_indices[feature_index].tolist()
        # target_distances = nbrs_distances[feature_index].tolist()

        return target_indices

    def expend_cluster(self, feature_index, neighbours, cluster_index, nbrs_indices):
        """
        根据现有的，没有visit过的点p，扩展cluster
        :param feature_index:
        :param neighbours:
        :param cluster_index: 聚类结果的下标，从0开始
        :return:
        """
        # neighbours = self.__query_neighbours(feature_index, nbrs_indices)
        # if len(neighbours) < self.min_pts:  # 不满足成为一个核心点的要求
        #     self.classifications[feature_index] = NOISE
        #     return False
        # else:
        #     self.classifications[feature_index] = cluster_index  # 将该点归入聚类中
        #
        # for index in neighbours:
        #     if self.classifications[index] == UNVISITED:  # 如果当前的点没有被遍历
        #         sub_neighbours = self.__query_neighbours(index, nbrs_indices)
        #         if len(sub_neighbours) >= self.min_pts:  # 如果有大于min_pts 的邻居，那么将这些邻居都加入　neighbours中
        #             for s_nei in sub_neighbours:
        #                 if s_nei not in neighbours:
        #                     neighbours.append(s_nei)
        #         self.classifications[index] = cluster_index  # index还不属于任何簇，那么加入当前簇中
        #
        #     if self.classifications[index] == NOISE:  # 已经visit过，但是还不属于任何一个簇
        #         self.classifications[index] = cluster_index  # index还不属于任何簇，那么加入当前簇中
        # return True

        self.classifications[feature_index] = cluster_index
        print '正在聚类: ', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for index in neighbours:
            if self.visit[index] == UNVISITED:
                self.visit[index] = VISITED
                sub_neighbours = self.__query_neighbours(index, nbrs_indices)
                if len(sub_neighbours) >= self.min_pts:
                    for s_nei in sub_neighbours:
                        if s_nei not in neighbours:
                            neighbours.append(s_nei)
            if self.classifications[index] == UNCLASSIFIED or self.classifications[index] == NOISE:
                self.classifications[index] = cluster_index

    def fit(self):
        """
        对输入的数据进行聚类
        :return:
        """
        self.classifications = [UNCLASSIFIED] * len(self.x_features_train)
        self.visit = [UNVISITED] * len(self.x_features_train)
        cluster_index = 0

        # 首先通过无监督的方式获取 该聚类之中 各个点最近的邻居的信息
        nbrs = NearestNeighbors(n_neighbors=int(math.ceil(self.min_pts)) + 1,
                                algorithm='auto').fit(self.x_features_train)
        nbrs_distances, nbrs_indices = nbrs.radius_neighbors(self.x_features_train, self.eps)

        for feature_index in range(len(self.x_features_train)):
            if self.visit[feature_index] == UNVISITED:

                neighbours = self.__query_neighbours(feature_index, nbrs_indices)
                self.visit[feature_index] = VISITED

                if len(neighbours) < self.min_pts:
                    self.classifications[feature_index] = NOISE
                else:
                    self.expend_cluster(feature_index, neighbours, cluster_index, nbrs_indices)
                    cluster_index += 1

        return self.get_cluster_result()

    def __save_cluster_result(self, clusters, noise):
        """
        将聚类的结果写入文件中
        :param clusters:
        :param noise:
        :return:
        """
        with codecs.open('dbscan-clusters.txt', 'wb', 'utf-8') as output_file:
            output_file.write('eps: ' + str(self.eps) + '\n')
            output_file.write('min_pts: ' + str(self.min_pts) + '\n')
            output_file.write('cluster count: ' + str(len(clusters.keys())) + '\n')
            for cluster_index, feature_index in clusters.items():
                info = [cluster_index] + feature_index
                info = [str(item) for item in info]
                output_file.write('\t'.join(info) + '\n')

        with codecs.open('dbscan-noise.txt', 'wb', 'utf-8') as output_file:
            output_file.write('noise count: ' + str(len(noise)) + '\n')
            info = [str(item) for item in noise]
            output_file.write('\t'.join(info) + '\n')

    def get_cluster_result(self):
        """
        获取聚类的结果信息
        :return:
            返回聚类结果以及噪音点信息
        """
        # model = DBSCAN(eps=self.eps, min_samples=self.min_pts, algorithm='auto')
        # x_features_train = self.x_features_train  # 训练数据属性
        # db = model.fit(x_features_train)
        # self.classifications = db.labels_.tolist()

        clusters = {}
        noises = []
        for index in range(len(self.classifications)):
            item = self.classifications[index]
            if item >= 0:
                if item in clusters.keys():
                    clusters[item].append(index)
                else:
                    clusters[item] = [index]
            elif item == UNVISITED:
                Exception('聚类过程中发生错误，还有未聚类的点！！')
            elif item == NOISE:
                noises.append(index)
        self.__save_cluster_result(clusters, noises)
        return clusters, noises


# def read_data(file_path='bezdekIris.data.txt', flag=0):
#     data_path = os.path.join('./', file_path)
#     df = pd.read_csv(data_path, header=None)
#
#     y_labels = df.iloc[0: 150, 4]
#     x_features = df.iloc[0: 150, 0: 4].values
#     return x_features, y_labels

# if __name__ == '__main__':
#     x_features, y_labels = read_data()
#     dbscan = Dbscan(x_features=x_features)
#     print dbscan.fit()
#     print np.array(dbscan.classifications)

    # model = DBSCAN(eps=0.39, min_samples=5.28, algorithm='auto')
    # x_features, y_labels = read_data(flag=0)
    # x_features_train = x_features  # 训练数据属性
    # y_labels_train = y_labels  # 训练数据标签
    # db = model.fit(x_features_train)
    # print db.labels_

    # nbrs = NearestNeighbors(n_neighbors=3, algorithm='auto').fit(x_features_train)
    # distances, indices = nbrs.radius_neighbors(x_features_train, 0.39)
    # print indices
    # print len(indices)
    # print distances
