#!/usr/bin/env python
# coding=utf-8
'''
@name aClickTrack.py
@desc 
@author xiezhen@baidu.com
@date 2018/03/30
'''
from math import tanh
import sqlite3

class searchnet:
    conn = None

    '''
    @desc 连接sqlite
    @param sqlite名字
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:21:36
    '''
    def __init__(self, dbname):
        self.conn = sqlite3.connect(dbname)

    '''
    @desc close conn
    @param None
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:22:06
    '''
    def __del__(self):
        self.conn.close()

    '''
    @desc 创建隐藏节点表，查询词URL对应表，隐藏节点URL对应表
    @param None
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:22:24
    '''
    def maketables(self):
        sql_list = [
                'create table hiddennode(create_key)',
                'create table wordhidden(from_id, to_id, strength)',
                'create table hiddenurl(from_id, to_id, strength)',
            ]
        for sql in sql_list:
            self.conn.execute(sql)

        self.conn.commit()

    '''
    @desc 删除隐藏节点表，查询词URL对应表，隐藏节点URL对应表
    @param None
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:23:21
    '''
    def droptables(self):
        sql_list = [
                'drop table hiddennode',
                'drop table wordhidden',
                'drop table hiddenurl',
            ]
        for sql in sql_list:
            self.conn.execute(sql)

        self.conn.commit()

    '''
    @desc 得到from_id到to_id边上的权重, 
          wordhidden默认权重-0.2，hiddenurl默认权重0
    @param from_id
    @param to_id
    @return 权重
    @author xiezhen@baidu.com
    @date 2018/03/30 17:23:43
    '''
    def getstrength(self, from_id, to_id, layer):
        if layer == 0:
            table = 'wordhidden'
        else:
            table = 'hiddenurl'

        sql = 'select strength from %s where from_id = %d and \
              to_id = %d' % (table, from_id, to_id)
        res = self.conn.execute(sql).fetchone()

        result = {
            0 : -0.2,
            1 : 0
        }
        if res == None:
            return result[layer]
        return res[0]

    '''
    @desc 设置from_id到to_id边上的权重,
    @param from_id
    @param to_id
    @param strength
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:25:05
    '''
    def setstrength(self, from_id, to_id, layer, strength):
        if layer == 0:
            table = 'wordhidden'
        else:
            table = 'hiddenurl'

        sql = 'select rowid from %s where from_id = %d and \
              to_id = %d' % (table, from_id, to_id)
        res = self.conn.execute(sql).fetchone()
        if res == None:
            sql = 'insert into %s (from_id, to_id, strength) \
                  values (%d, %d, %f)' % (table, from_id, to_id, strength)
        else:
            rowid = res[0]
            sql = 'update %s set strength=%f where rowid = %d' % (table, strength, rowid)
        res = self.conn.execute(sql)
        self.conn.commit()

    '''
    @desc 给定查询词，和URL，查看是否有对应的隐藏节点，如果没有则创建隐藏节点
    @param wordids
    @param urls
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:25:48
    '''
    def generatehiddennode(self, wordids, urls):
        if len(wordids) > 3:
            return None
        create_key = '_'.join(sorted([str(wi) for wi in wordids]))
        table = 'hiddennode'
        sql = "select rowid from '%s' where create_key = '%s'" % (table, create_key)
        res = self.conn.execute(sql).fetchone()
        if res == None:
            sql = "insert into '%s' (create_key) values ('%s')" % (table, create_key)
            res = self.conn.execute(sql)
            hiddenid = res.lastrowid
            for wordid in wordids:
                self.setstrength(wordid, hiddenid, 0, 1.0 / len(wordids))
            for urlid in urls:
                self.setstrength(hiddenid, urlid, 1, 0.1)
            self.conn.commit()

    '''
    @desc 给定查询词，和URL，给出所有的隐藏节点
    @param wordids
    @param urls
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:25:48
    '''
    def getallhiddenids(self, wordids, urlids):
        l1 = {}
        for wordid in wordids:
            sql = 'select to_id from wordhidden where from_id=%d' % wordid
            cur = self.conn.execute(sql)
            for row in cur:
                l1[row[0]] = 1

        for urlid in urlids:
            sql = 'select from_id from hiddenurl where to_id=%d' % urlid
            cur = self.conn.execute(sql)
            for row in cur:
                l1[row[0]] = 1

        return l1.keys()

    '''
    @desc 初始化神经网络
    @param wordids
    @param urlids
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:51:33
    '''
    def setupnetwork(self, wordids, urlids):
        #值列表
        self.wordids = wordids
        self.hiddenids = self.getallhiddenids(wordids, urlids)
        self.urlids = urlids

        # 节点输出
        self.ai = [1.0] * len(self.wordids)
        self.ah = [1.0] * len(self.hiddenids)
        self.ao = [1.0] * len(self.urlids)

        # 权重矩阵
        self.wi = [
                [self.getstrength(wordid, hiddenid, 0)
                 for hiddenid in self.hiddenids]
                 for wordid in self.wordids
                ]
        self.wo = [
                [self.getstrength(hiddenid, urlid, 1)
                 for urlid in self.urlids]
                 for hiddenid in self.hiddenids
                ]

    '''
    @desc 前馈法，将每个节点的值初始化
    @param None 
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:52:12
    '''
    def feedforward(self):
        for i in range(len(self.wordids)):
            self.ai[i] = 1.0

        for j in range(len(self.hiddenids)):
            sumRet = 0.0
            for i in range(len(self.wordids)):
                sumRet += self.ai[i] * self.wi[i][j]
            self.ah[j] = tanh(sumRet)

        for k in range(len(self.urlids)):
            sumRet = 0.0
            for j in range(len(self.hiddenids)):
                sumRet += self.ah[j] * self.wo[j][k]
            self.ao[k] = tanh(sumRet)

        return self.ao[:]

    '''
    @desc 查看当前神经网络各个点的值
    @param wordids
    @param urlids
    @return 输出节点的概率
    @author xiezhen@baidu.com
    @date 2018/03/30 17:53:04
    '''
    def getreault(self, wordids, urlids):
        self.setupnetwork(wordids, urlids)
        return self.feedforward()

    '''
    @desc 计算tanh的斜率
    @param tanh
    @return 斜率
    @author xiezhen@baidu.com
    @date 2018/03/30 17:54:08
    '''
    def dtanh(self, y):
        return 1.0 - y * y

    '''
    @desc 反向传播算法
    @param 目标值
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:54:41
    '''
    def backPropagate(self, targets, N=0.5):
        #计算输出层误差
        output_deltas = [0.0] * len(self.urlids)
        for k in range(len(self.urlids)):
            error = targets[k] - self.ao[k]
            output_deltas[k] = error * self.dtanh(self.ao[k])
        #计算隐藏层误差
        hidden_deltas = [0.0] * len(self.hiddenids)
        for j in range(len(self.hiddenids)):
            error = 0.0
            for k in range(len(self.urlids)):
                error += output_deltas[k] * self.wo[j][k]
            hidden_deltas[j] = self.dtanh(self.ah[j]) * error
        #更新输出权重
        for j in range(len(self.hiddenids)):
            for k in range(len(self.urlids)):
                change = output_deltas[k] * self.ah[j]
                self.wo[j][k] += N * change

        #更新输入权重
        for i in range(len(self.wordids)):
            for j in range(len(self.hiddenids)):
                change = hidden_deltas[j] * self.ai[i]
                self.wi[i][j] += N * change

    '''
    @desc 更新数据库
    @param None
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:55:13
    '''
    def updatedatabase(self):
        for i in range(len(self.wordids)):
            for j in range(len(self.hiddenids)):
                self.setstrength(self.wordids[i], self.hiddenids[j], 0, self.wi[i][j])

        for j in range(len(self.hiddenids)):
            for k in range(len(self.urlids)):
                self.setstrength(self.hiddenids[j], self.urlids[k], 1, self.wo[j][k])
        self.conn.commit()
        
    '''
    @desc 训练数据 
    @param wordids
    @param urlids
    @param 目标wordids对应的url
    @return None
    @author xiezhen@baidu.com
    @date 2018/03/30 17:55:29
    '''
    def trainquery(self, wordids, urlids, selectedurl):
        self.generatehiddennode(wordids, urlids)

        self.setupnetwork(wordids, urlids)
        self.feedforward()

        targets = [0.0] * len(urlids)
        targets[urlids.index(selectedurl)] = 1.0
        self.backPropagate(targets)
        self.updatedatabase()

def test():
    mynet = searchnet('nn.db')
    #mynet.maketables()
    #mynet.droptables()
    #print mynet.getstrength(0, 0, 0)
    #print mynet.setstrength(0, 0, 0, 0.1)
    #wWorld, wRiver, wBank = 101, 102, 103
    #uWorldBank, uRiver, uEarth = 201, 202, 203
    #mynet.generatehiddennode([wWorld, wBank], [uWorldBank, uRiver, uEarth])
    #for c in mynet.conn.execute('select * from wordhidden'):
    #    print c
    #for c in mynet.conn.execute('select * from hiddenurl'):
    #    print c
 
if __name__ == '__main__':
    mynet = searchnet('nn.db')
    # 输入
    wWorld, wRiver, wBank = 101, 102, 103
    uWorldBank, uRiver, uEarth = 201, 202, 203
    # 训练
    mynet.trainquery(
            [wWorld, wBank],
            [uWorldBank, uRiver, uEarth],
            uWorldBank
        )
    # 得到结果
    print mynet.getreault(
            [wWorld, wBank],
            [uWorldBank, uRiver, uEarth]
            ) 
