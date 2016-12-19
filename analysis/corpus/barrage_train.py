#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import codecs
import glob
import multiprocessing
import os
from multiprocessing import Pool

import gensim

from util.loader.dataloader import get_barrage_from_txt_file
from wordsegment.wordseg import segment_barrages

from gensim import utils
from gensim.models.doc2vec import TaggedDocument
from gensim.models import Doc2Vec

from random import shuffle
from util.fileutil import FileUtil


class TrainSentences(object):
    # 参数： barrage_corpus_dirname 弹幕语料的路径
    #       barrage_corpus_file_type 弹幕语料存储的文件类型
    def __init__(self, barrage_corpus_dirname, barrage_corpus_file_type="txt"):
        self.barrage_corpus_file_type = barrage_corpus_file_type.lower()
        self.barrage_corpus_dirname = barrage_corpus_dirname

    # if our input is strewn across several files on disk, with one sentence per line, then instead of loading
    #  everything into an in-memory list, we can process the input file by file, line by line
    def __iter__(self):
        # sentences = MySentences('/some/directory') # a memory-friendly iterator
        with codecs.open("all-input-corpus.txt", "rb", "utf-8") as input_file:
            for line in input_file:
                yield line.strip().split(u"\t")


class LabeledLineSentence(object):

    def __init__(self, corpus_file):
        self.sentences = []
        self.prefix = "CORPUS_SENTECE_"
        self.corpus_file = corpus_file

    def __iter__(self):
        for uid, line in enumerate(open(self.corpus_file)):
            yield TaggedDocument(words=line.split(), tags=[(self.prefix + '%s') % uid])

    def to_array(self):
        self.sentences = []
        for uid, line in enumerate(open(self.corpus_file)):
            self.sentences.append(
                TaggedDocument(utils.to_unicode(line).split(), [self.prefix + '_%s' % uid]))
        return self.sentences

    def sentences_perm(self):
        shuffle(self.sentences)
        return self.sentences


# 多线程生成分词文件信息
def gen_corpus_words():
    barrage_corpus_files = glob.glob(os.path.join(FileUtil.get_corpus_dir(), "*.txt"))
    file_lists = [barrage_corpus_files[0: 501], barrage_corpus_files[501: 1001], barrage_corpus_files[1001: 1501],
                  barrage_corpus_files[1501: 2001], barrage_corpus_files[2001: 2501], barrage_corpus_files[2501: 3001],
                  barrage_corpus_files[3001: len(barrage_corpus_files)]]
    pools = Pool(7)
    file_index = 0
    for file_list in file_lists:
        file_index += 1
        pools.apply_async(gen_corpus_words_internal, args=(file_list, "all-corpus-" + str(file_index) + ".txt"))
    pools.close()
    pools.join()


# 对于每一个弹幕语料文件，都对其中的的弹幕进行切词，将切词的结果写入语料文件夹中。
def gen_corpus_words_internal(barrage_corpus_files, save_corpus_file_path):
    file_count = 0
    with codecs.open(save_corpus_file_path, "wb", "utf-8") as output_file:
        for barrage_corpus_file in barrage_corpus_files:
            file_count += 1
            print unicode(str(file_count))
            print unicode(barrage_corpus_file)
            barrages = get_barrage_from_txt_file(barrage_corpus_file)
            barrage_seg_list = segment_barrages(barrages, is_corpus=True)
            # 开始将分词之后的结果写入语料文件中，每条弹幕的分词结果占一行，每个词语用tab分割。
            #  convert to unicode, lowercase, remove numbers, extract named entities…
            for barrage_seg in barrage_seg_list:
                corpus_words = u""
                if len(barrage_seg.sentence_seg_list) <= 0:
                    continue  # 弹幕中的词语有可能全部被替换掉了，没有剩下任何词语。
                for word_seg in barrage_seg.sentence_seg_list:
                    corpus_words += (word_seg.word + u"\t")
                corpus_words = corpus_words[0: len(corpus_words) - 1] + u"\n"
                output_file.write(corpus_words)


# 根据语料库建立 word2vec 模型
# 参数： barrage_corpus_dirname 弹幕语料的路径
#       barrage_corpus_file_type 弹幕语料存储的文件类型
def build_word2vec_model(barrage_corpus_dirname, barrage_corpus_file_type="txt"):
    train_sentences = TrainSentences(barrage_corpus_dirname, barrage_corpus_file_type)
    """
    min_count: One of them is for pruning the internal dictionary. Words that appear only once or twice in a billion-word corpus
    are probably uninteresting typos and garbage. In addition, there’s not enough data to make any meaningful training
    on those words, so it’s best to ignore them, default 5
    size: Another parameter is the size of the NN layers, which correspond to the “degrees” of freedom the training
     algorithm has, default 100
    workers: training parallelization, to speed up training, default = 1 worker = no parallelization
    """
    model = gensim.models.Word2Vec(train_sentences, min_count=5, size=150, workers=multiprocessing.cpu_count())
    model.save(os.path.join(FileUtil.get_train_model_dir(), "barrage-corpusword2vec-model.txt"))


def build_doc2vec_model(corpus_file):
    train_sentences = LabeledLineSentence(corpus_file)
    model = Doc2Vec(min_count=1, window=10, size=100, sample=1e-4, workers=multiprocessing.cpu_count(), alpha=0.025)
    model.build_vocab(train_sentences.to_array())

    for epoch in range(50):
        model.train(train_sentences.sentences_perm())

    model.save('./d2v.txt')


if __name__ == "__main__":
    # train_sentences = TrainSentences(FileUtil.get_corpus_dir())
    # gen_corpus_words()

    # build_doc2vec_model()
    save_corpus_path = '../../data/local/8752370-save.txt'

    build_doc2vec_model(save_corpus_path)