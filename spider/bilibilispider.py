#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import argparse
import codecs
import os
import re
import sched
import time
from multiprocessing import Pool

# from db.dao.barragedao import BarrageDao
# from db.dao.videodao import VideoDao
from spider import BarrageSpider
from util.datetimeutil import DateTimeUtil
from util.fileutil import FileUtil
from util.loggerutil import Logger

"""
抓取bilibili站点的视频信息（标题，分类）以及视频对应的弹幕信息。
"""

__author__ = "htwxujian@gmail.com"

logger = Logger("video-url-spider.log").get_logger()

"""
BilibiliBarrageSpider 爬取b站的弹幕信息，通过调用start函数爬取相关视频的弹幕信息，video_url 为b站的url信息。
如果输入其他的链接，那么将会出错。
"""


class BilibiliSpider(BarrageSpider):
    def __init__(self):
        # 确保父类被正确初始化了
        # http://stackoverflow.com/questions/21063228/typeerror-in-python-single-inheritance-with-super-attribute
        super(BilibiliSpider, self).__init__()

    # -----------------------------------------------------------------------------------------------------------------
    # 视频信息获取部分
    # -----------------------------------------------------------------------------------------------------------------
    # 获得视频的标题信息
    def get_video_title(self, html_content):
        pattern = re.compile(r'<div\sclass="v-title"><h1.*?>(.*?)</h1></div>', re.S)
        match = re.search(pattern, html_content)
        if match is None:
            return None
        title = match.group(1)
        return title

    # 获得视频的meta keywords信息。
    def get_video_meta_keywords(self, html_content):
        pattern = re.compile(r'<meta\sname="keywords"\scontent="(.*?)".*?/>', re.S)
        match = re.search(pattern, html_content)
        if match is None:
            return None
        meta_keywords = u"\t".join(match.group(1).strip().split(","))
        return meta_keywords

    # 获取视频的观看数，总弹幕数（但是实际获取不到这么多），投币数，收藏数。
    # 这个数据是由js脚本自动生成的，现在这个代码无法获取。。。。
    def get_video_title_info(self, html_content):
        pattern = re.compile(r'<div\sclass="v-title-info">.*?<span\sid="dianji">(.*?)</span>.*?<span\sid="dm_count">(.*?)</span>.*?<span\sid="v_ctimes">(.*?)</span>.*?<span\sid="stow_count">(.*?)</span>.*?</div>', re.S)
        match = re.search(pattern, html_content)
        if match is None:
            return None
        video_title_info = match.groups()
        return video_title_info

    # 获得视频的标签信息，比如：主页 > 动画 > MMD·3D，存下来是这样的格式：主页\t动画\tMMD.3D 这样的格式。
    def get_video_tags(self, html_content):
        pattern = re.compile(r'<span\stypeof="v:Breadcrumb"><a\shref=.*?\srel="v:url"\sproperty="v:title">(.*?)' +
                             '</a></span>', re.S)
        match = re.findall(pattern, html_content)
        if match is None:
            return None
        tags = u"\t".join(match)
        return tags

    # 获得跟视频弹幕对应的cid信息。
    def get_video_cid(self, html_content):
        pattern = re.compile(r'.*?<script.*>EmbedPlayer\(\'player\',.*?"cid=(\d*)&.*?</script>', re.S)
        match = re.search(pattern, html_content)
        if match is not None:
            cid = match.group(1).strip()
            return cid
        pattern = re.compile(r'<embed.*?class="player".*?flashvars="bili-cid=(.*?)&.*?</embed>',
                             re.S)
        match = re.search(pattern, html_content)
        if match is not None:
            cid = match.group(1).strip()
            return cid
        pattern = re.compile(
            r'<div.*?id="bofqi">.*?<iframe.*?src=".*?cid=(.*?)&.*?".*?>.*?</iframe>.*?</div>', re.S)
        match = re.search(pattern, html_content)
        if match is not None:
            cid = match.group(1).strip()
            return cid
        return u"-1"  # 找不到cid的情况

    # 获得视频的id信息。
    def get_video_aid(self, video_url):
        pattern = re.compile(r'http://.*?/.*?/av(.*?)/.*?', re.S)
        match = re.search(pattern, video_url)
        if match is None:
            return None
        mid = match.group(1).strip()
        return unicode(mid)

    # 构建弹幕的xml链接地址。
    def barrage_xml_url(self, cid):
        if cid is None:
            return None
        xml_url = "http://comment.bilibili.tv/" + cid + ".xml"
        print xml_url
        return xml_url

    # -----------------------------------------------------------------------------------------------------------------
    # 弹幕信息获取部分
    # -----------------------------------------------------------------------------------------------------------------
    # 获得弹幕xml链接地址上的全部弹幕信息。
    def get_row_video_barrage(self, barrage_xml_url):
        # 获取弹幕网页的源代码
        barrage_html = self.get_response_content(barrage_xml_url)
        # 弹幕出现的播放时间，弹幕类型，字体大小，字体颜色，弹幕出现的unix时间戳，弹幕池，弹幕创建者id，弹幕id
        pattern = re.compile(r'<d p="(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?)">(.*?)</d>', re.S)
        barrages = re.findall(pattern, barrage_html)
        # 返回全部的弹幕信息
        return barrages

    # -----------------------------------------------------------------------------------------------------------------
    # 弹幕信息存储部分
    # -----------------------------------------------------------------------------------------------------------------
    # 获得更新的弹幕列表。与之前存在于本地的弹幕数据进行对比，从而得到当前更新的弹幕数据。
    def get_refresh_video_barrage(self, cid, row_barrages):
        barrage_file_path = FileUtil.get_barrage_file_path(cid)
        # 检查该cid的弹幕文件是否存在，如果不存在，那么此时的row_barrages数据将全部写入文件中，
        # 如果存在，那么就只要找到更新的弹幕记录。
        barrage_count = 0
        if FileUtil.is_file_exists(barrage_file_path):
            last_barrage_index = -1  # 记录文件中最后一条弹幕在row_barrages中的下标。
            barrage_count = FileUtil.get_file_line_count(barrage_file_path)
            last_n_barrages = FileUtil.get_file_last_n_line_content(barrage_file_path, 5)
            Logger.print_console_info(u"当前文件的最后n条弹幕：\n" + u"\n".join(last_n_barrages))
            for index in xrange(len(row_barrages) - 1, -1, -1):
                if self.__is_same_barrage(last_n_barrages, row_barrages[index]):
                    # 获得存储在弹幕文件中的最后一条弹幕，在更新弹幕序列中的位置。
                    last_barrage_index = index
                    break
            # 当前弹幕数据没有更新
            if last_barrage_index == (len(row_barrages) - 1):
                row_barrages = []
                Logger.print_console_info(unicode(DateTimeUtil.get_cur_timestamp("%Y-%m-%d %H:%M:%S")) +
                                               u"\t" + u"弹幕数据没有更新。")
            # 此时部分的弹幕数据需要更新
            elif last_barrage_index >= 0:
                Logger.print_console_info(unicode(DateTimeUtil.get_cur_timestamp("%Y-%m-%d %H:%M:%S")) +
                                               u"\t" + u"有弹幕数据更新：" +
                                               u"\t" + str(len(row_barrages) - last_barrage_index - 1))
                row_barrages = row_barrages[last_barrage_index + 1: len(row_barrages)]
            # 弹幕全文都要更新
            elif last_barrage_index == -1:
                Logger.print_console_info(unicode(DateTimeUtil.get_cur_timestamp("%Y-%m-%d %H:%M:%S")) + u"\t" +
                                               u"有弹幕数据更新：" + u"\t" + str(len(row_barrages)))
        barrage_count += len(row_barrages)
        Logger.print_console_info(unicode(DateTimeUtil.get_cur_timestamp("%Y-%m-%d %H:%M:%S")) +
                                       u" 当前弹幕总条数：" + unicode(barrage_count) + u"\n\n")
        return row_barrages

    # 将弹幕信息写入文件中。
    # 参数：cid 视频对应的cid信息（基于b站）
    #      row_barrages 当前已经更新的弹幕信息列表
    #      is_corpus 当前的弹幕信息是否作为语料存储，默认为false，不作为语料存储
    def save_barrages_to_local(self, cid, row_barrages, is_corpus=False):
        barrage_count = len(row_barrages)
        if barrage_count <= 0:  # 是对于要存储入数据库的弹幕来说的。
            return
        barrage_file_path = FileUtil.get_barrage_file_path(cid, is_corpus)
        if is_corpus:
            if barrage_count < 100:  # 弹幕数量小于100的弹幕不作为语料库弹幕数据。
                return
            row_barrages = self.sort_barrages(row_barrages)
            # 如果需要作为语料库的信息，那么 弹幕数量 频率至少为每10秒钟 一条，这样才能保持内容的连贯性。
            try:
                total_seconds = float(row_barrages[-1][0].strip())
                if (total_seconds / 10) > barrage_count:
                    return
            except Exception as exception:
                print exception
                return
        with codecs.open(barrage_file_path, "ab", "utf-8") as output_file:
            for barrage in row_barrages:
                if barrage is not None:
                    output_file.write(u"\t".join(barrage) + u"\n")

    # 判断 row_barrages 中的某一条弹幕记录 与 本地文件中最后n条弹幕的某一条是否相同。
    def __is_same_barrage(self, last_n_barrages, barrage):
        # barrage 格式：(row_id, play_timestamp, ... , content)
        # last_n_barrages 格式：[last_barrage, last_barrage, ...]
        for last_barrage in last_n_barrages:
            # last_barrage 格式: (row_id\tplay_timestamp\t...\tcontent)
            last_barrage = last_barrage.split(u"\t")
            if len(last_barrage) != len(barrage):
                Logger.print_console_info(u"Error，弹幕格式有误，无法两条弹幕是否相同。")
                continue
            is_same = True
            for index in xrange(1, len(last_barrage)):
                if last_barrage[index] != barrage[index]:
                    is_same = False
                    break
            if is_same:
                return True
        return False

    # 抓取网页的视频以及弹幕信息。（弹幕信息是必须写入本地文件的，写入数据库的功能是基于写入本地文件的基础上的
    # 写入数据库的时候需要 根据 本地文件中的弹幕数据判断，当前哪一些弹幕是已经更新的弹幕。）
    # 参数： video_url  视频的链接信息
    #       is_save_to_db 是否要将弹幕信息写入数据库
    #       is_corpus 写入到本地的弹幕文件是否以语料的方式存储，默认为false，不作为语料存储
    #       season_id  番剧的id信息，该字段不为null时，表示当前视频为番剧的一集
    #       season_index  当前视频为番剧的第几集
    def start_spider_barrage(self, video_url, is_save_to_db=True, is_corpus=False, season_id=None, season_index=None):
        print u"进入 start_spider_barrage 函数。"
        # 视频网页的html源码信息。
        video_html_content = self.get_response_content(video_url)
        if video_html_content is None:
            # 说明网络连接可能有问题，导致无法获得网页源码。
            Logger.print_console_info(u"无法获得网页html代码，请检查网址是否输入正确，或检查网络连接是否正常！！")
            return None
        # 获得视频的相关信息
        aid = self.get_video_aid(video_url)
        cid = self.get_video_cid(video_html_content)
        tags = self.get_video_tags(video_html_content)
        title = self.get_video_title(video_html_content)
        meta_keywords = self.get_video_meta_keywords(video_html_content)

        # 获取弹幕信息。
        barrages = self.get_row_video_barrage(self.barrage_xml_url(cid))
        if barrages is None:  # 弹幕xml文件解析失败的时候，会返回none
            return
        # 将更新后的弹幕信息写入数据库。
        if is_save_to_db:
            # 将视频信息存储入数据库中
            # VideoDao.add_video(cid, title, tags, meta_keywords, aid, unicode(video_url), season_id, season_index)
            # 获取更新的弹幕信息。
            barrages = self.get_refresh_video_barrage(cid, barrages)
            # BarrageDao.add_barrages(barrages, aid)
        # 将更新后的弹幕信息写入本地文件。
        self.save_barrages_to_local(cid, barrages, is_corpus)

    # -----------------------------------------------------------------------------------------------------------------
    # 视频，音频下载部分。
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    # 某一大类型下的视频链接获取相关（在获取语料库的时候，爬取某一个类型下的弹幕数据时使用。）
    # -----------------------------------------------------------------------------------------------------------------
    # 获取视频列表的页数信息
    def get_video_list_page_count(self, html_content):
        pattern = re.compile(r'<div class="pagelistbox">.*?<a class="p endPage".*?>(\d+)</a>.*?</div>', re.S)
        match = re.search(pattern, html_content)
        if match is None:
            return None
        page_count = int(match.group(1))
        return page_count

    # 构建 按照 弹幕量排序的，进三个月的，全部页数的 视频列表 页面信息。
    def get_relative_video_list_urls(self, page_count, base_url):
        video_list_urls = []
        # order_param = "order=damku"
        # # 构建 近三个月的 时间范围字符串
        # now_date = datetime.date.today()
        # now_date_str = now_date.strftime("%Y-%m-%d")
        # # 这种方式会出现 月份天数不同的问题，比如今天是4月30号，三个月前没有2月30号。
        # # pass_date_str = datetime.datetime(now_date.year, now_date.month - 2, now_date.day).strftime("%Y-%m-%d")
        # pass_date_str = (now_date - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
        # date_range_param = "range=" + pass_date_str + "," + now_date_str
        param_construct_method = -1  # 视频列表链接的参数构造信息
        split_info = base_url.split("/")
        video_base_url = "/".join(split_info[0: len(split_info) - 1])  # http://www.bilibili.com/video
        movie_detail_param = split_info[len(split_info) - 1]
        split_info = movie_detail_param.split("_")
        if len(split_info) < 3:  # 还有用 - 来分割的
            split_info = movie_detail_param.split("-")
            if len(split_info) < 3:
                split_info = ""
            else:
                param_construct_method = 1
        else:
            param_construct_method = 0
            # 就是为了构建 http://www.bilibili.com/video/movie_japan_1.html 这样的链接
            movie_detail_param = "_".join(split_info[0: len(split_info) - 1]) + "_"
        for index in xrange(1, page_count + 1):
            # page_param = "page=" + str(index)
            # link = base_url + "#!" + page_param + "&" + date_range_param + "&" + order_param
            if param_construct_method == 0:
                link = video_base_url + "/" + movie_detail_param + str(index) + ".html"
            elif param_construct_method == 1:
                link = base_url + "#!page=" + str(index)
            else:
                continue
            video_list_urls.append(link)
        return video_list_urls

    # 获得 按弹幕量 排序的 视频url信息。弹幕数量超过100的视频。
    # 参数： barrage_threshold 视频的弹幕数量必须超过 barrage_threshold 才能被选取
    #       video_list_urls 包含视频链接信息的 视频列表页面链接
    def get_video_urls(self, video_list_urls, barrage_threshold=100):
        video_urls = []
        for video_list_url in video_list_urls:
            html_content = self.get_response_content(video_list_url)
            pattern = re.compile(
                r'<div class="l-r"><a href="(.*?)".*?>.*?</a><div class="v-desc">.*?</div>.*?<i class="b-icon b-icon-v-dm".*?></i><span number=".*?">(.*?)</span>',
                re.S)
            temp_video_urls_info = re.findall(pattern, html_content)
            if temp_video_urls_info is None:
                continue
            for video_url_info in temp_video_urls_info:
                # http://www.bilibili.com/video/av4482900/
                video_url = "http://www.bilibili.com" + video_url_info[0]
                barrage_count = video_url_info[1]
                if barrage_count < barrage_threshold:
                    continue  # 忽略弹幕数量小于100的视频
                video_urls.append(video_url)
        return video_urls

    # 抓取视频的链接信息
    # 完整链接：http://www.bilibili.com/video/movie_japan_1.html#!page=8&range=2016-02-30,2016-04-30&order=damku
    # 输入的bilibili链接为：http://www.bilibili.com/video/movie_japan_1.html
    # 其他的部分：page、range、order自己构建
    def start_collect_barrage_corpus(self, bilibili_url):
        logger.debug(u"进入 start_spider_video_url 函数！！")
        # 获得视频弹幕排序网页的网页源代码
        html_content = self.get_response_content(bilibili_url)
        video_list_page_count = self.get_video_list_page_count(html_content)
        # 获得视频列表 页面的 页数url信息（第一页到最后一页）
        video_list_urls = self.get_relative_video_list_urls(video_list_page_count, bilibili_url)
        # 获得该列表页面下所有的视频链接信息
        video_urls = self.get_video_urls(video_list_urls)
        for video_url in video_urls:
            logger.debug(u"开始抓取 " + unicode(video_url) + u"弹幕信息")
            self.start_spider_barrage(video_url=video_url, is_save_to_db=False, is_corpus=True)


# ----------------------------------------------------------关于弹幕的语料信息------------------------------------------#
# -------------------------------------------------------------------------------------------------------------------#
# 收集弹幕语料信息，收集弹幕的语料信息。
def collect_barrage_corpus():
    bilibili_spider = BilibiliSpider()
    video_categories_url = []
    with codecs.open("barrage-corpus.txt", "rb", "utf-8") as input_file:
        for line in input_file:
            url = line.strip().split("\t")[0]
            video_categories_url.append(url)
    for video_category_url in video_categories_url:
        bilibili_spider.start_collect_barrage_corpus(video_category_url)


# ----------------------------------------------------------关于多进程收集弹幕数据------------------------------------------#
# -------------------------------------------------------------------------------------------------------------------#
# 爬取弹幕的任务函数。
def grab_barrage_task(video_url):
    Logger.print_console_info(u"子进程id：%s，抓取网页：%s。开始……" % (os.getpid(), video_url))
    bili_spider = BilibiliSpider()
    bili_spider.start_spider_barrage(video_url)
    Logger.print_console_info(u"子进程id：%s，抓取网页：%s。结束……" % (os.getpid(), video_url))


# 爬虫主函数，创建多个进程对多个video站点的弹幕信息进行抓取。
def main():
    arg_parser = argparse.ArgumentParser(u"BilibiliSpider", description=u"grabs the barrages from bilibili video" +
                                                                        u" and store barrages to db.")
    arg_parser.add_argument("-u", "-urls", required=False, action="append", metavar="BILIBILI_VIDEO_URLS", default=[],
                            dest="video_urls", help="the bilibili video urls.")
    arg_parser.add_argument("-i", "--internal", required=False, metavar="INTERNAL_TIME", default=5,
                            dest="internal_time",
                            help="the internal minute for grabing the bilibili barrages")
    opts = arg_parser.parse_args()
    video_urls = opts.video_urls  # 获得url的list列表。
    video_urls = ["http://www.bilibili.com/video/av2218236/index_1.html",
                  "http://www.bilibili.com/video/av2218236/index_2.html",
                  "http://www.bilibili.com/video/av2218236/index_3.html",
                  "http://www.bilibili.com/video/av2218236/index_4.html",
                  "http://www.bilibili.com/video/av2218236/index_5.html",
                  "http://www.bilibili.com/video/av2218236/index_6.html",
                  "http://www.bilibili.com/video/av2218236/index_7.html"]
    print video_urls

    Logger.print_console_info(u"开始抓取弹幕信息。\n父进程id：%s" % os.getpid())
    pool = Pool(7)
    for video_url in video_urls:
        print video_url
        pool.apply_async(grab_barrage_task, args=(video_url,))
    pool.close()
    pool.join()
    Logger.print_console_info(u"弹幕信息抓取结束！")


def scheme_task(my_sched, interval_time=60):
    main()
    my_sched.enter(interval_time, 0, scheme_task, (my_sched, interval_time))


def scheme_main(interval_time=60):
    s = sched.scheduler(time.time, time.sleep)
    s.enter(interval_time, 0, scheme_task, (s, interval_time))
    s.run()
# -------------------------------------------------------------------------------------------------------------------#
# -------------------------------------------------------------------------------------------------------------------#


if __name__ == "__main__":
    #scheme_main(60)
    bilibili_spider = BilibiliSpider()
    # bilibili_spider.start_collect_barrage_corpus("http://www.bilibili.com/video/movie_japan_1.html")
    # collect_barrage_corpus()
    bilibili_spider.start_spider_barrage("http://www.bilibili.com/video/av5384127/")
