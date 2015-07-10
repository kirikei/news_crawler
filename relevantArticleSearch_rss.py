#!/usr/bin/env python
# -*- coding: utf-8 -*-
import feedparser
import argparse
import sys
import urllib
from time import mktime
from datetime import datetime
from BeautifulSoup import BeautifulSoup
from boilerpipe.extract import Extractor
import requests
import grequests
from OutputFactory import OutputFactory
import hashlib

#とりあえずRSSで取得することにする
class googleSearch(object):
    # FIXME:parameter設定部分は後で見直すこと
    def __init__(self, **args):
        self.set_params(args)
        self.header = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

    def search(self,**args):
        if args != {}:
            self.set_params(args)
        self.feed = feedparser.parse(self.url)

    #RSSで受け取ったentry用，取り敢えず．
    def parse_entity(self):
        self.entries = [dict() for i in range(len(self.feed['entries']))]
        entries = self.feed['entries']
        self.urls = []
        i = 0
        for entry in entries:
            splitedStrings = entry['title'].split(" - ")
            self.entries[i]['title'] = ''.join(splitedStrings[0:len(splitedStrings)-1])
            self.entries[i]['media'] = ''.join(splitedStrings[len(splitedStrings)-1:len(splitedStrings)])
            self.entries[i]['moreLink'] = BeautifulSoup(entry['summary']).find('a',{'class' : 'p'}).get('href')
            self.entries[i]['img'] = BeautifulSoup(entry['summary']).find('img').get('src')
            self.entries[i]['publishedDate'] = datetime.fromtimestamp(mktime(entry['published_parsed'])).strftime('%Y/%m/%d %H:%M')
            self.entries[i]['link'] = entry['link']
            self.urls.append(entry['link'])

            self.entries[i]['summary'] = Extractor(html=entry['summary']).getText()
            self.entries[i]['aid'] = hashlib.sha1(entry['title'].encode('utf-8')).hexdigest()
            self.entries[i]['pid'] = self.pid
            self.entries[i]['tid'] = self.topic
            # for case can not fetch
            self.entries[i]['text'] = None
            i+=1

    # TODO: write with boilerpipe
    # for extract text from origin sources
    def fetch_articles(self):
        greq_gen = (grequests.get(u, headers=self.header,) for u in self.urls)
        responses = grequests.map(greq_gen)
        for i,res in enumerate(responses):
            if res is not None:
                extractor = Extractor(html=res.text)
                self.entries[i]['text'] = extractor.getText()
                if '...' in self.entries[i]['title']:
                    self.entries[i]['title'] = extractor.getTitle()
        
        return True

    def extract_realtime_coverage(self):
        _entries = []
        for entry in self.entries:
            coverage_url = "http://news.google.com/news?output=rss&" +  entry['moreLink'].split('?')[1]
            pid = entry['aid']
            gs = googleSearch(pid=pid,url=coverage_url,topic=self.topic)
            
            gs.search()
            gs.parse_entity()
            gs.fetch_articles()

            _entries += gs.entries
        self.entries += _entries
        
    def output(self):
        if self.entries == []:
            return False
        of = OutputFactory(self.outputType, self.output_filename)
        of.write(self.entries)

    def set_params(self,args):
        params = {}
        #refer to http://blog.slashpoundbang.com/post/12975232033/google-news-search-parameters-the-missing-manual

        if "pid" in args:
            self.pid = args['pid']
        else:
            self.pid = None

        if "outputType" in args:
            self.outputType = args["outputType"]
            self.output_filename = ""
            if self.outputType == 'db':
                self.output_filename = 'relevant_news.db'
            elif self.outputType == 'json':
                self.output_filename = "result.json"
        else:
            self.outputType = "json"
            self.output_filename = "result.json"

        # for url params
        if "url" in args:
            self.url = args['url']
            self.topic = args['topic']
        else:
            if "base_url" in args:
                self.url = args["base_url"]
            else:
                self.url = "http://news.google.com/news?output=rss"

            # NOTE:only enabled one of either
            if "q" in args:
                self.query = args["q"]
                params['q'] = self.query
                self.topic = ""
            else:
                if "topic" in args:
                    self.topic = args["topic"]
                else:
                    self.topic = "h" #topトピック
                params['topic'] = self.topic

            if "hostLanguage" in args:
                self.hostLanguage = args["hostLanguage"]
            else:
                self.hostLanguage = "us"
            params['hl'] = self.hostLanguage

            if "num" in args:
                self.articleNum = args['num']
            else:
                self.articleNum = str(100)
            params['num'] = self.articleNum

            #ned をUSにしないとRSS取得出来ないのでus固定
            self.specificCountry = "us"
            params['ned'] = self.specificCountry
            self.url += '&' + urllib.urlencode(params)

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='search')
    argparser.add_argument('-q',action='store',dest='q')
    argparser.add_argument('-t',action='store',dest='topic')
    argparser.add_argument('-hl',action='store',dest='hl')
    argparser.add_argument('-n',action='store',dest='num')
    argparser.add_argument('-o',action='store',dest='outputType')
    argparser.add_argument('-p',action='store',dest='pid')
    argparser.add_argument('-e',action='store_true',dest='extract_coverage',default=False)

    if len(sys.argv) > 1:
        argv = vars(argparser.parse_args(sys.argv[1:]))
        argv = dict((k, v) for k, v in argv.items() if v is not None)
        gs = googleSearch(**argv)
        gs.search()
        gs.parse_entity()
        gs.fetch_articles()
        article_count = len(gs.entries)
        coverage_count = 0
        if argv['extract_coverage'] is True:
            gs.extract_realtime_coverage()
            coverage_count = len(gs.entries) - article_count
        gs.output()
        print '{0} - {1} topic, {2} articles and {3} coverages done.'.format(datetime.today().strftime('%Y/%m/%d %H:%M:%S'),argv['topic'],article_count,coverage_count)
        # for e in sorted(gs.entries,key=lambda d:d['publishedDate']):
        #     # print(datetime.strftime(e['publishedDate'],'%Y/%m/%d %H:%M') + ' : ' + e['title'] + ' - '+ e['source'])
        #     print('{0} : {1} - {2}'.format(e['publishedDate'],e['title'],e['source']))

