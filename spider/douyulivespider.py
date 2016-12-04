#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
抓取斗鱼弹幕的信息，并且存储到当前文件夹下。
"""

import codecs
import hashlib
import json
import re
import socket
import sys
import threading
import time
import urllib
import urllib2
import uuid


class DouyuProtocolMsg(object):

    # content为协议的数据内容
    def __init__(self, content):

        self.msg_type = bytearray([0xb1, 0x02, 0x00, 0x00])
        # python3 中的byte类型，对应2.x版本的八位串
        self.content = bytes(content.decode("utf-8", "ignore"))
        # 数据包必须以 \0 结尾
        self.end = bytearray([0x00])
        self.length = bytearray([len(self.content) + 9, 0x00, 0x00, 0x00])
        self.code = self.length

    # 获得整个协议包的byte数组
    def get_bytes(self):
        return bytes(self.length + self.code + self.msg_type + self.content + self.end)


class DouyuBarrageClient:

    # liveUrl 主播的链接地址
    def __init__(self, live_url):

        self.live_html_code = self.__grab_html_code(live_url)  # 必须首先调用

        self.barrage_servers = ""  # 弹幕服务器
        self.login_auth_servers = self.__init_auth_servers()  # 登陆验证服务器

        self.login_user_name = ""  # 登陆用户名
        self.live_stat = ""  # 登陆状态字段
        self.weight = ""  # 主播财产
        self.fans_count = ""  # 直播间粉丝数量

        self.room = self.__init_room_info()  # 主播房间信息
        self.grp_id = ""  # 用户在直播间的组id
        self.dev_id = str(uuid.uuid4()).replace("-", "").upper()
        self.ver = "20150929"  # 发送协议中表示版本号，固定值
        self.socket_buffer_size = 4096

        self.file_system_encoding = sys.getfilesystemencoding()

        self.barrage_auth_socket = ""  # 用于验证登陆的socket
        self.barrage_socket = ""  # 用于获取弹幕的socket

    # 登陆弹幕服务器
    def do_login(self):

        # 挑选一对验证服务器地址和端口
        auth_server = self.login_auth_servers[0]["ip"]
        auth_port = int(self.login_auth_servers[0]["port"])
        self.barrage_auth_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.barrage_auth_socket.connect((auth_server, auth_port))
        # 向验证服务器发送验证请求，获得username, rid, gid信息。
        self.do_login_auth()
        # 向弹幕服务器发送登陆请求
        barrage_server = self.barrage_servers[0][0]
        barrage_port = int(self.barrage_servers[0][1])
        self.barrage_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.barrage_socket.connect((barrage_server, barrage_port))
        self.do_login_barrage()

    # 保持心跳数据
    def keeplive(self):

        print u"启动 KeepLive 线程"
        while True:
            self.send_auth_keeplive_req()
            self.send_barrage_keeplive_req()
            time.sleep(40)

    def send_auth_keeplive_req(self):

        content = "type@=keeplive/tick@=" + self.__timestamp() + "/vbw@=0/k@=19beba41da8ac2b4c7895a66cab81e23/"
        msg = self.__protocol_msg(content)
        self.barrage_auth_socket.send(msg)

    def send_barrage_keeplive_req(self):

        content = "type@=keeplive/tick@=" + self.__timestamp() + "/"
        msg = self.__protocol_msg(content)
        self.barrage_socket.send(msg)

    # 向验证服务器发送登陆请求
    def do_login_auth(self):
        self.__send_auth_loginreq_req()
        self.__parse_auth_loginreq_resp()

    # 向弹幕服务器发送登陆请求
    def do_login_barrage(self):

        self.__send_barrage_loginreq_req()  # 发送登陆弹幕服务器请求
        # 这时的回应信息没有用处
        self.barrage_socket.recv(self.socket_buffer_size)
        # 向服务器发送加入群组的信息
        self.__send_barrage_join_grp_req()
        # 这两条请求发送完成之后就可以接受弹幕了

    # 向验证登陆服务器发送验证登陆信息
    def __send_auth_loginreq_req(self):

        rt = self.__timestamp()  # 发送协议中包含的字段，值为以秒为单位的时间戳
        vk = self.__vk(rt, self.dev_id)
        # 开始构建发送包的内容部分
        content = "type@=loginreq/username@=/ct@=0/password@=1234567890123456/roomid@=" + self.room["id"] + "/devid@="\
                  + self.dev_id + "/rt@=" + rt + "/vk@=" + vk + "/ver@=" + self.ver + "/"
        msg = self.__protocol_msg(content)
        self.barrage_auth_socket.send(msg)

    # 解析验证服务器返回的两个信息
    # 在第一个回馈信息中可获得username
    # 在第二个回馈信息中可获得 弹幕服务器列表、主播房间编号，用户在直播间的组编号
    def __parse_auth_loginreq_resp(self):

        # 获得之后的登陆用户名
        server_resp = self.barrage_auth_socket.recv(self.socket_buffer_size)
        server_resp = self.__filter_escape_character(server_resp)
        pattern = re.compile(r'username@=(.*?)/.*?live_stat@=(.*?)/', re.S)
        match = re.search(pattern, server_resp)
        self.login_user_name = match.group(1)
        self.live_stat = match.group(2)

        # 获得弹幕服务器列表
        server_resp = self.barrage_auth_socket.recv(self.socket_buffer_size)
        server_resp = self.__filter_escape_character(server_resp)
        pattern = re.compile(r'id@A=.*?ip@A=(.*?)/port@A=(.*?)/', re.S)
        self.barrage_servers = re.findall(pattern, server_resp)
        print server_resp

        # 获得房间编号 rid，以及用户分组编号gid
        pattern = re.compile(r'type@=setmsggroup/rid@=(.*?)/gid@=(.*?)/.*?weight@=(.*?)/.*?fans_count@=(.*?)/', re.S)
        match = re.search(pattern, server_resp)
        self.room["id"] = match.group(1)
        self.grp_id = match.group(2)
        self.weight = match.group(3)
        self.fans_count = match.group(4)

    # 向弹幕服务器发送登陆信息
    def __send_barrage_loginreq_req(self):

        content = "type@=loginreq/username@=" + self.login_user_name + "/password@=1234567890123456/roomid@=" + self.room["id"] + "/"
        msg = self.__protocol_msg(content)
        self.barrage_socket.send(msg)

    # 向弹幕服务器发送加入直播室群组的信息
    def __send_barrage_join_grp_req(self):

        # gid=-9999 表示未分组，接受所有的弹幕信息
        content = "type@=joingroup/rid@=" + self.room["id"] + "/gid@=-9999/"
        msg = self.__protocol_msg(content)
        self.barrage_socket.send(msg)

    # 过滤掉转义字符串
    def __filter_escape_character(self, my_str):

        return my_str.replace("@A", "@").replace("@S", "/")

    # 构建请求协议信息
    def __protocol_msg(self, content):

        return DouyuProtocolMsg(content).get_bytes()

    # 获得网页源代码信息
    def __grab_html_code(self, live_url):

        request = urllib2.Request(live_url)
        response = urllib2.urlopen(request)
        return response.read()

    # 检查获得的json信息是否有效
    def __valid_json(self, my_json):

        try:
            json_object = json.loads(my_json)
        except ValueError as e:
            print e
            return False
        return json_object

    # 获得主播房间信息
    def __init_room_info(self):

        # 为什么 var\s\$ROOM\s=\s({.*}) 这个正则表达式可以，r'var\s\$ROOM\s=\s{(.*)}' 就不行
        room_info_json = re.search('var\s\$ROOM\s=\s({.*})', self.live_html_code).group(1)
        room_info_json_format = self.__valid_json(room_info_json)
        room = {}
        if room_info_json_format is not False:
            js = room_info_json_format
            room["id"] = str(js["room_id"])
            room["name"] = js["room_name"]
            room["ggShow"] = js["room_gg"]["show"]
            room["ownerUid"] = str(js["owner_uid"])
            room["ownerName"] = js["owner_name"]
            room["roomUrl"] = js["room_url"]
            room["nearShowTime"] = js["near_show_time"]
            room["tags"] = js["all_tag_list"]
        return room

    # 打印主播房间的信息
    def print_room_info(self):

        if self.room == {} or self.room is None:
            print u"暂未获得主播房间信息"
        else:
            print u"================================================"
            print u"= 直播间信息"
            print u"================================================"
            print u"= 房间：" + self.room["name"] + u"\t编号：" + self.room["id"]
            print u"= 主播：" + self.room["ownerName"] + u"\t编号：" + self.room["ownerUid"]
            tags = u""
            for key in self.room["tags"]:
                tags += (self.room["tags"][key]["name"] + u"\t")
            print (u"= 标签：" + tags).encode(self.file_system_encoding, "ignore")
            print u"= 粉丝：" + self.fans_count
            print u"= 财产：" + self.weight
            # <[^<]+?>  这个正则表达式什么意思？
            print (u"= 公告：" + re.sub("\n+", "\n", re.sub("<[^<]+?>", "", self.room["ggShow"]))).encode(self.file_system_encoding, "ignore")
            print u"================================================"

    # 获得验证服务器的列表
    def __init_auth_servers(self):

        pattern = re.compile(r'"server_config":"(.*?)","', re.S)
        match = re.search(pattern, self.live_html_code)
        ori_urls = match.group(1)
        ori_urls = urllib.unquote(ori_urls)
        return json.loads(ori_urls)

    # 构建以秒为单位的时间戳
    def __timestamp(self):

        return str(int(time.time()))

    # 获得发送协议中vk的值
    def __vk(self, timestamp, dev_id):

        return hashlib.md5(timestamp + "7oE9nPEG9xXV69phU31FYCLUagKeYtsF" + dev_id).hexdigest()

    # 获得弹幕信息
    def get_barrage(self, output_file):

        try:
            # 文集的 open 操作如果在此处，那么文件打开操作太过频繁，导致弹幕写入不了文件
            server_resp = self.barrage_socket.recv(4000)
            server_resp = self.__filter_escape_character(server_resp).decode("utf-8", "ignore")
            msgType = re.search(r"type@=(.*?)/", server_resp).group(1)
            if msgType == "chatmsg":
                rid = re.search(r"rid@=(.*?)/", server_resp).group(1)  # 房间id
                uid = re.search(r"uid@=(.*?)/", server_resp).group(1)  # 发送者id
                nn = re.search(r"nn@=(.*?)/", server_resp).group(1)  # 发送者昵称
                txt = re.search(r"txt@=(.*?)/", server_resp).group(1)  # 弹幕文本内容
                cid = re.search(r"cid@=(.*?)/", server_resp).group(1)  # 弹幕唯一id
                level = re.search(r"level@=(.*?)/", server_resp).group(1)  # 用户等级
                output_file.write(unicode(str(time.time())) + u"\t" + rid + u"\t" + uid + u"\t" + nn + u"\t" + txt + u"\t" + cid + u"\t" + level + u"\n")
                print (unicode(str(time.time())) + u"\t" + rid + u"\t" + uid + u"\t" + nn + u"\t" + txt + u"\t" + cid + u"\t" + level + u"\n").encode(self.file_system_encoding, "ignore")
            elif msgType == "chatmessage":
                rid = re.search(r"rid@=(.*?)/", server_resp).group(1)  # 房间id
                sender = re.search(r"sender@=(.*?)/", server_resp).group(1)  # 发送者id
                snick = re.search(r"snick@=(.*?)/", server_resp).group(1)  # 发送者昵称
                content = re.search(r"content@=(.*?)/", server_resp).group(1)  # 弹幕文本内容
                chat_msg_id = re.search(r"chatmsgid@=(.*?)/", server_resp).group(1)  # 弹幕唯一id
                level = re.search(r"level@=(.*?)/", server_resp).group(1)  # 用户等级
                output_file.write(unicode(str(time.time())) + u"\t" + rid + u"\t" + sender + u"\t" + snick + u"\t" + content + u"\t" + chat_msg_id + u"\t" + level + u"\n")
                print (unicode(str(time.time())) + u"\t" + rid + u"\t" + sender + u"\t" + snick + u"\t" + content + u"\t" + chat_msg_id + u"\t" + level + u"\n").encode(self.file_system_encoding, "ignore")
        except AttributeError as e:
            print e

    def start(self):
        self.do_login()  # 登陆验证服务器，以及弹幕服务器
        if self.live_stat == 0:
            print u"主播离线中，正在退出…………"
        else:  # 主播在线的状态
            print u"主播在线中，准备获取弹幕…………"
            self.print_room_info()
            keeplive_thread = threading.Thread(target=self.keeplive)
            keeplive_thread.setDaemon(True)
            keeplive_thread.start()
            # 保存弹幕数据
            barrage_file_name = self.room["id"] + "_" + time.strftime("%Y-%m-%d") + ".txt"
            with codecs.open(barrage_file_name, "ab", "utf-8") as outputFile:
                while True:
                    self.get_barrage(outputFile)

if __name__ == "__main__":
    live_url = sys.argv[1]
    dc = DouyuBarrageClient(live_url)
    dc.start()
