# TSCAnalysis

#### 环境要求
1. python 包
> jieba gensim


> 数据库不用管了，弹幕数据不存在数据库里
> mysql-connector(mac 上) mysqldb(windows 上)


2. 运行
> 直接运行 TSCAnalysis/spider/bilibilispider.py文件，在以下代码中修改视频链接，
获得的弹幕文件存储在 TSCAnalysis/data/local 目录下：
```
if __name__ == "__main__":
    bilibili_spider = BilibiliSpider()
    # 可以写一个视频url文件，然后从文件中读入，以后在改善
    bilibili_spider.start_spider_barrage("http://www.bilibili.com/video/av5384127/")
```
---

2. 数据库要求
> 1. mysql版本 >= 5.5.3
> 2. mysqldb 版本 >= 1.2.5

*原因：由于弹幕数据中包含大量的特殊unicode字符，需要使用mysql中的utf8mb4编码方式存储（完全支持全部的unicode字符串），而mysql的5.5.3 版本及以上，mysqldb的1.2.5版本及以上支持utf8mb4编码。*

3. 关于mysql utf8mb4 的配置
> 1. Ubuntu MySQL configuration file (/etc/my.cnf)
> 2.  Windows: my.ini

    关于mysql utf8mb4 的配置
    
    [client]
    default-character-set = utf8mb4

    [mysql]
    default-character-set = utf8mb4

    [mysqld]
    character-set-client-handshake = FALSE
    character-set-server = utf8mb4
    collation-server = utf8mb4_unicode_ci
    
> 3. 停止mysql服务，修改完成my.cnf(my.ini)之后,重启mysql服务即可。





