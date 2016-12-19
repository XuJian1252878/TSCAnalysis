#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import codecs
import re

from analysis.model.dictconfig import DictConfig

"""
对于一个句子来说，分词之后会有很多个词语，需要在这些词语中将不需要的词语过滤出去，
这个模块里的函数主要提供这样的过滤功能。
"""


# 判断一个词语是否是停用词，是则返回true，不是则返回false。
def is_stopwords(word):
    stopwords_set = DictConfig.get_stopwords_set()
    if word in stopwords_set:
        return True
    else:
        return False


# 如果词语在替换词词典中，那么返回(True, 替换之后的词)，否则返回(Flase, 原词)
# 替换词词典的顺序是严格讲究的。
def format_word(word, flag):
    replace_word_list = DictConfig.get_replace_words_list()
    for replace_pattern_info in replace_word_list:
        replace_pattern = replace_pattern_info[0]
        replace_word = replace_pattern_info[1]
        replace_flag = replace_pattern_info[2]
        pattern = re.compile(replace_pattern)
        match = re.match(pattern, word)
        if match is not None:
            return True, replace_word, replace_flag
    return False, word, flag


# 判断一个词语是否为符号或者是数字，如果是，那么返回True，否则返回False
def is_num_or_punctuation(word, flag):
    reject_punctuation_set = DictConfig.get_reject_punctuation_dict()
    reject_word_flag_set = set(["w", "m"])  # set(["w", "m", "eng"])
    if flag in reject_word_flag_set:
        __record_reject_word_info(word, flag)  # 看看被过滤掉的都是什么词，调试用
        return True
    if word in reject_punctuation_set:
        return True
    return False


# word 待替换的词语信息，flag word的词性，word_start_position word在原句中的起始位置，
# word_end_position word在原句中的结束位置
# 对弹幕中的颜表情进行替换，如果颜表情在替换词词典中，
# 那么返回(True, [替换之后的词, 替换后的词性，表情在原句中的起始位置，表情在原句中的结束位置])，
# 否则返回(Flase, [原词, 原词词性，表情在原句中的起始位置，表情在原句中的结束位置])
# replace_emoji_to_word函数中会将匹配上的 单个 emoji 表情的词语属性 替换成emoji。
def replace_emoji_to_word(word, flag, word_start_position, word_end_position):
    emoji_replace_dict = DictConfig.get_emoji_replace_dict()
    emoji_set = emoji_replace_dict.keys()
    result_emoji = []  # 因为有些人两个颜文字会连发，所以需要辨别其中的多个表情。
    first_match_flag = False
    emoji_start_position = word_start_position - 1
    emoji_end_position = word_start_position - 1
    # 从word 头部开始判断emoji表情是否存在
    while word != "":
        find_flag = False
        for emoji in emoji_set:
            if word == emoji:
                emoji_start_position = emoji_end_position + 1  # 当前表情在原句中的起始位置
                emoji_end_position = emoji_start_position - 1 + len(emoji)  # 当前表情在原句中的结束位置
                if len(result_emoji) <= 0:
                    if len(word) == 1:
                        return True, [(emoji_replace_dict[emoji], "emoji", emoji_start_position, emoji_end_position)]
                    return True, [(emoji_replace_dict[emoji], flag, emoji_start_position, emoji_end_position)]
                else:
                    if len(word) == 1:
                        result_emoji.append((emoji_replace_dict[emoji], "emoji",
                                             emoji_start_position, emoji_end_position))
                    result_emoji.append((emoji_replace_dict[emoji], flag, emoji_start_position, emoji_end_position))
                    return True, result_emoji
            # 多个颜文字一起发的情况，解决判断多个重复颜文字问题。
            find_flag = word.startswith(emoji)
            if find_flag:
                emoji_start_position = emoji_end_position + 1  # 当前表情在原句中的起始位置
                emoji_end_position = emoji_start_position - 1 + len(emoji)  # 当前表情在原句中的结束位置
                result_emoji.append((emoji_replace_dict[emoji], "emoji", emoji_start_position, emoji_end_position))
                word = word.replace(emoji, "", 1)
                if not first_match_flag:
                    first_match_flag = True
                break
        if not find_flag:  # 没有找到对应的表情
            break

    # 从头开始匹配失败，那么从尾开始匹配试一试。
    if not first_match_flag:
        while word != "":
            find_flag = False
            for emoji in emoji_set:
                # 多个颜文字一起发的情况，解决判断多个重复颜文字问题。
                find_flag = word.endswith(emoji)
                if find_flag:
                    emoji_start_position = emoji_end_position + 1  # 当前表情在原句中的起始位置
                    emoji_end_position = emoji_start_position - 1 + len(emoji)  # 当前表情在原句中的结束位置
                    result_emoji.append((emoji_replace_dict[emoji], "emoji", emoji_start_position, emoji_end_position))
                    word = word.replace(emoji, "", 1)
                    break
            if not find_flag:  # 没有找到对应的表情
                break

    # if word != "":
    #     result_emoji.append(word, "emoji-unknow")  # 没有被收录到词典中的表情
    if len(result_emoji) <= 0:
        if flag == "emoji":  # 没有识别出来的颜文字。。。或者符号。。。舍弃掉。。。
            __record_reject_word_info(word, flag)  # 调试用，看看都舍弃了一些什么符号。
            return False, None
        else:
            return False, [(word, flag)]
    else:
        return True, result_emoji


# 判断一个词的词性是否为接受的词性，若是，那么返回true；否则返回false。
def is_accept_nominal(nominal):
    accept_nominal_set = DictConfig.get_accept_nominal_set()
    for accept_nominal in accept_nominal_set:
        # 因为词性都是大类之内再分为小类，如w、n等等；结巴分词的结果可能直接把小类分了出来，如wp、wn等等
        # 所以词性判断需要使用startwith来判断。
        if accept_nominal.startswith(nominal):
            return True
    return False


# 由于结巴分词会将颜文字表情识别为一个个的单一标点符号，使原来的颜文字表情信息无法表示出来。
# 这里做一个整合，当发现一个 连续的标点符号串 ， 并且长度大于等于2的时候，那么我们认为这个标点符号串是一个emoji颜文字表情。
# 这时我们将这一串的 连续标点符号串 作为一个词语，属性为emoji。
# 但是 ❤ 这种颜文字只有一个字符，这样的话在这里我们就不能将它标注为emoji。因为上面的限制一旦放宽到大于等于1，
# 那么，。这种无意义的单个标点也会被识别为emoji，这不可取。（这里待改进）。但是影响不大，因为在replace_emoji_to_word函数中，根据词典
# 都能替换成情感词，另外replace_emoji_to_word函数中会将匹配上的 单个 emoji 表情的词语属性 替换成emoji。
# 输入参数：words为一个句子的结巴分词结果。
def distinguish_emoji(words):
    # 找到连续的标点符号（长度大于等于2），作为emoji表情
    punctuation_index_list = []
    punctuation_list = []
    emoji_replace_list = []
    result_words = []  # 用于返回的结果列表
    words_index = -1
    for word, flag in words:
        words_index += 1
        result_words.append((word, flag))  # 存储分词结果列表，作为返回结果
        if flag == "x":  # 如果当前词性 被识别为 字符串
            if len(punctuation_index_list) <= 0:
                punctuation_list.append(word)
            elif words_index - punctuation_index_list[-1] == 1:
                # 表明是连续的标点符号
                punctuation_list.append(word)
            punctuation_index_list.append(words_index)
        else:
            # 当前词性不是标点符号的时候
            if len(punctuation_list) > 0:
                if len(punctuation_list) >= 2:
                    # 说明此时已经识别出了一个emoji表情
                    emoji_pic = u"".join(punctuation_list)
                    emoji_replace_list.append((punctuation_index_list[0], punctuation_index_list[-1], emoji_pic))
                # 清空原来的记录信息（punctuation_list 可能是emoji表情或者是单个标点符号）
                punctuation_index_list = []
                punctuation_list = []
    # emoji刚好在最末尾的时候
    if len(punctuation_list) >= 2:
        # 说明此时已经识别出了一个emoji表情
        emoji_pic = u"".join(punctuation_list)
        emoji_replace_list.append((punctuation_index_list[0], punctuation_index_list[-1], emoji_pic))
    # 开始替换emoji表情
    for index in xrange(len(emoji_replace_list) - 1, -1, -1):
        replace_start_index = emoji_replace_list[index][0]
        replace_end_index = emoji_replace_list[index][1]
        emoji_pic = emoji_replace_list[index][2]
        result_words = result_words[0: replace_start_index] + [(emoji_pic, "emoji")] + \
                       result_words[replace_end_index + 1: len(result_words)]
    return result_words


# 记录舍弃掉的词语信息，用于调试。
def __record_reject_word_info(word, flag):
    with codecs.open("reject_word_info.txt", "ab", "utf-8") as output_file:
        output_file.write(word + u"\t" + flag + u"\n")


# 判断词语是否有效词（有效词指的是 扩展后的情感词典、程度副词词典、否定词词典中包括的词）
# 如果词语是情感词词典中的词，那么返回该情感词对应的情感类别情感词，便于今后的时间窗口划分
# 如果词语是程度副词词典或者否定词词典中的词，那么返回原词信息。
# 如果词语不再这三个词典中，那么返回词信息。
# 返回格式：(true or false,  word_info)
def judge_valid_word(word):
    emotion_dict = DictConfig.load_emotion_dict()
    # 填充情感词信息。
    emotion_word_dict = {}
    for category, word_info in emotion_dict.items():
        for word_item in word_info:
            word = word_item[0]
            if word not in emotion_word_dict.keys():
                emotion_word_dict[word] = category
    # 否定词词典
    negatives_set = DictConfig.load_negatives_set()
    # 程度副词词典
    degree_adverb_dict = DictConfig.load_degree_adverb_dict()
    if word in emotion_dict.keys():
        return True, emotion_dict[word]
    elif (word in negatives_set) or (word in degree_adverb_dict.keys()):
        return True, word
    else:
        return False, None


if __name__ == "__main__":
    DictConfig.build_dicts()
    print format_word("22333333")
