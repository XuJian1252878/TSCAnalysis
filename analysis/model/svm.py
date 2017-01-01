# coding=utf-8
from numpy import *


# 自定义数据结构
class DataStructure:
    # 初始化数据结构中的参数
    def __init__(self, data_set, label_set, c, boundary, kernel_type):
        self.data = data_set
        self.label = label_set
        self.c = c
        self.boundary = boundary
        self.n = shape(data_set)[0]
        self.alphas = mat(zeros((self.n, 1)))
        self.b = 0
        # 缓存Ek，第一列用于判断是否有效
        self.ekCache = mat(zeros((self.n, 2)))
        self.k = mat(zeros((self.n, self.n)))
        for i in range(self.n):
            self.k[:, i] = kernel_function(self.data, self.data[i, :], kernel_type)


# 核函数，将数据映射到高维空间，解决数据在原始空间中线性不可分的问题
def kernel_function(data_set, x, kernel_type):
    m, n = shape(data_set)
    k = mat(zeros((m, 1)))
    # Linear Kernel：线性可分的情况使用线性核函数
    if kernel_type[0] == 'linear':
        k = data_set * x.T
    # RBF Kernel：低维线性不可分的情况进行高维线性化
    elif kernel_type[0] == 'RBF':
        # 计算与每行之间的欧氏距离
        for i in range(m):
            distance = data_set[i, :] - x
            k[i] = distance * distance.T
        # 用户自定义调控参数
        k = exp(k / (-2 * kernel_type[1] * kernel_type[1]))
    else:
        print 'Please input an identifiable kernel type.'
    return k


# SMO算法：确定目标函数中的参数“alpha”，其中默认的核函数为线性核
def smo(data_set, label_set, c, max_iter, boundary, kernel_type=('linear', 0)):
    ds = DataStructure(mat(data_set), mat(label_set).transpose(), c, boundary, kernel_type)
    iterations = 0    # 迭代次数
    entire_iter = True    # 判断是否需要遍历所有的alpha
    alpha_pairs_changed = 0
    while (iterations < max_iter) and ((alpha_pairs_changed > 0) or entire_iter):
        alpha_pairs_changed = 0
        # 每回迭代的第一次需遍历出所有的alpha
        if entire_iter:
            for i in range(ds.n):
                ei = calc_ei(ds, i)
                # 判断是否达到预期误差
                if ((ds.label[i] * ei < (-1 * ds.boundary)) and (ds.alphas[i] < ds.c)) or ((ds.label[i] * ei > ds.boundary) and (ds.alphas[i] > 0)):
                    # 利用启发式算法根据i选择j，并计算Ej
                    j, ej = select_alpha_j(i, ei, ds)
                    orig_alpha_i = ds.alphas[i].copy()
                    orig_alpha_j = ds.alphas[j].copy()
                    # 确定上下界
                    if ds.label[i] != ds.label[j]:
                        l = max(0, ds.alphas[j] - ds.alphas[i])
                        h = min(ds.c, ds.c + ds.alphas[j] - ds.alphas[i])
                    else:
                        l = max(0, ds.alphas[j] + ds.alphas[i] - ds.c)
                        h = min(ds.c, ds.alphas[j] + ds.alphas[i])
                    if l == h:
                        # print "L=H"
                        continue
                    # 更新alpha（j）公式中的n
                    n = ds.k[i, i] + ds.k[j, j] - 2.0 * ds.k[i, j]
                    if n <= 0:
                        # print "The value of n is error."
                        continue
                    # 根据公式更新alpha（j）
                    ds.alphas[j] += ds.label[j] * (ei - ej) / n
                    # 根据上下界更新alpha（j）
                    if ds.alphas[j] > h:
                        ds.alphas[j] = h
                    if l > ds.alphas[j]:
                        ds.alphas[j] = l
                    # 将更新后的ej值存入cache中
                    update_ei(ds, j)
                    if abs(ds.alphas[j] - orig_alpha_j) < 0.00001:
                        continue
                    # 根据alpha（j）更新alpha（i）
                    ds.alphas[i] += ds.label[j] * ds.label[i] * (orig_alpha_j - ds.alphas[j])
                    # 更新cache中对应ei值
                    update_ei(ds, i)
                    # 对b值进行更新
                    b1 = ds.b - ei - ds.label[i] * (ds.alphas[i] - orig_alpha_i) * ds.k[i, i] - ds.label[j] * (ds.alphas[j] - orig_alpha_j) * ds.k[i, j]
                    b2 = ds.b - ei - ds.label[j] * (ds.alphas[i] - orig_alpha_i) * ds.k[i, j] - ds.label[j] * (ds.alphas[j] - orig_alpha_j) * ds.k[j, j]
                    if (ds.alphas[i] > 0) and (ds.alphas[i] < ds.c):
                        ds.b = b1
                    elif (ds.alphas[j] > 0) and (ds.alphas[j] < ds.c):
                        ds.b = b2
                    else:
                        ds.b = (b1 + b2) / 2.0
                    alpha_pairs_changed += 1
                else:
                    continue
            iterations += 1
        # 继续遍历满足KKT条件的alpha
        else:
            valid_alpha = nonzero((ds.alphas.A > 0) * (ds.alphas.A < c))[0]
            for i in valid_alpha:
                ei = calc_ei(ds, i)
                # 判断是否达到预期误差
                if ((ds.label[i] * ei < -ds.boundary) and (ds.alphas[i] < ds.c)) or ((ds.label[i] * ei > ds.boundary) and (ds.alphas[i] > 0)):
                    # 利用启发式算法根据i选择j，并计算Ej
                    j, ej = select_alpha_j(i, ei, ds)
                    orig_alpha_i = ds.alphas[i].copy()
                    orig_alpha_j = ds.alphas[j].copy()
                    # 确定上下界
                    if ds.label[i] != ds.label[j]:
                        l = max(0, ds.alphas[j] - ds.alphas[i])
                        h = min(ds.c, ds.c + ds.alphas[j] - ds.alphas[i])
                    else:
                        l = max(0, ds.alphas[j] + ds.alphas[i] - ds.c)
                        h = min(ds.c, ds.alphas[j] + ds.alphas[i])
                    if l == h:
                        # print "L=H"
                        continue
                    # 更新alpha（j）公式中的n
                    n = ds.k[i, i] + ds.k[j, j] - 2.0 * ds.k[i, j]
                    if n <= 0:
                        # print "The value of n is error."
                        continue
                    # 根据公式更新alpha（j）
                    ds.alphas[j] += ds.label[j] * (ei - ej) / n
                    # 根据上下界更新alpha（j）
                    if ds.alphas[j] > h:
                        ds.alphas[j] = h
                    if l > ds.alphas[j]:
                        ds.alphas[j] = l
                    # 将更新后的ej值存入cache中
                    update_ei(ds, j)
                    if abs(ds.alphas[j] - orig_alpha_j) < 0.00001:
                        continue
                    # 根据alpha（j）更新alpha（i）
                    ds.alphas[i] += ds.label[j] * ds.label[i] * (orig_alpha_j - ds.alphas[j])
                    # 更新cache中对应ei值
                    update_ei(ds, i)
                    # 对b值进行更新
                    b1 = ds.b - ei - ds.label[i] * (ds.alphas[i] - orig_alpha_i) * ds.k[i, i] - ds.label[j] * (ds.alphas[j] - orig_alpha_j) * ds.k[i, j]
                    b2 = ds.b - ei - ds.label[j] * (ds.alphas[i] - orig_alpha_i) * ds.k[i, j] - ds.label[j] * (ds.alphas[j] - orig_alpha_j) * ds.k[j, j]
                    if (ds.alphas[i] > 0) and (ds.alphas[i] < ds.c):
                        ds.b = b1
                    elif (ds.alphas[j] > 0) and (ds.alphas[j] < ds.c):
                        ds.b = b2
                    else:
                        ds.b = (b1 + b2) / 2.0
                    alpha_pairs_changed += 1
                else:
                    continue
            iterations += 1
        if entire_iter:
            entire_iter = False
        elif alpha_pairs_changed == 0:
            entire_iter = True
        print "Iteration number: %d" % iterations
    return ds.alphas, ds.b


# 计算预测值与真实值之差（Ei）
def calc_ei(ds, i):
    # 预测值
    f_xi = float(multiply(ds.alphas, ds.label).T * ds.k[:, i] + ds.b)
    # 预测值与真实值之差
    ei = f_xi - float(ds.label[i])
    return ei


# 启发式算法：根据alpha（i）确定alpha（j），从而完成SMO算法的第一步，一对alpha的选取
def select_alpha_j(i, ei, ds):
    max_j = -1
    max_e = 0
    ej = 0
    ds.ekCache[i] = [1, ei]    # 设置为有效值
    valid_cache_list = nonzero(ds.ekCache[:, 0].A)[0]
    if (len(valid_cache_list)) > 1:
        # 遍历整个ekCahe，找到一个能使得“delta_e”最大的ej
        for k in valid_cache_list:
            # 不再考虑ei
            if k == i:
                continue
            ek = calc_ei(ds, k)
            delta_e = abs(ei - ek)
            # “delta_e”最大
            if delta_e > max_e:
                max_j = k
                max_e = delta_e
                ej = ek
        return max_j, ej
    # ekCache的值仅有1个（初次遍历）
    else:
        # 随机选取一个
        j = i
        while j == i:
            j = int(random.uniform(0, ds.n))
            ej = calc_ei(ds, j)
    return j, ej


# 将更新后的ei值放到cache中
def update_ei(ds, i):
    ei = calc_ei(ds, i)
    ds.ekCache[i] = [1, ei]


# OVR SVMs：将二分类的SVM扩展为多分类
def multi_classi(train_data, train_label, test_data):
    m, n = shape(train_data)
    multi_label = []  # 多分类label
    predict_set = zeros((m, 2))
    # 初始化预测集合
    for pre_i in range(m):
        predict_set[pre_i, 0] = -10
        predict_set[pre_i, 1] = train_label[0]
    # 构造该数据集的多分类label
    multi_label.append(train_label[0])
    for i in range(shape(train_label)[0]):
        label_judge = True
        # 判断是否为新类别
        for j in range(shape(multi_label)[0]):
            if multi_label[j] == train_label[i]:
                label_judge = False
                break
        if label_judge:
            multi_label.append(train_label[i])
    # 一对多进行多次训练，选取最大的预测值作为分类结果
    for k in range(shape(multi_label)[0]):
        tmp_label = []  # 将多分类label构造成一个二分类label
        for l in range(shape(train_label)[0]):
            if train_label[l] == multi_label[k]:
                tmp_label.append(1)
            else:
                tmp_label.append(-1)
        alphas, b = smo(train_data, tmp_label, 200, 6000, 0.00001, ('RBF', 1.3))
        # 测试集数据
        data_mat = mat(test_data)
        label_mat = mat(tmp_label).transpose()
        sv_index = nonzero(alphas.A > 0)[0]
        sv = data_mat[sv_index]  # 根据alpha获取支持向量
        label_sv = label_mat[sv_index]
        m1, n1 = shape(data_mat)
        for o in range(m1):
            kernel = kernel_function(sv, data_mat[o, :], ('RBF', 1.3))
            predict = kernel.T * multiply(label_sv, alphas[sv_index]) + b
            if predict > predict_set[o, 0]:
                predict_set[o, 0] = predict
                predict_set[o, 1] = multi_label[k]
    return predict_set[:, 1]


# 读取数据
def load_data(file_name):
    data_set = []
    label_set = []
    f_open = open(file_name)
    for line in f_open.readlines():
        line_array = line.strip().split('\t')
        data_set.append([float(line_array[0]), float(line_array[1]), float(line_array[2]), float(line_array[3]), float(line_array[4]), float(line_array[5]), float(line_array[6])])
        label_set.append(float(line_array[7]))
    return data_set, label_set


if __name__ == '__main__':
    # test 调用示例
    train_data, train_label = load_data("seeds_dataset.txt")
    predict_s = multi_classi(train_data, train_label, train_data)
    errorCount = 0
    datMat = mat(train_data)
    m, n = shape(datMat)
    for i in range(m):
        print "%d: %f, %f" % (i + 1, predict_s[i], train_label[i])
        if predict_s[i] != train_label[i]:
            errorCount += 1
    print "the test error rate is: %f" % (float(errorCount) / m)
