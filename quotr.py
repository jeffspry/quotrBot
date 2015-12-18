import praw
import time
import datetime
import re
import os
import urllib
import requests
import json
from goog import getQuotes
from collections import OrderedDict

__author__ = '/u/spookyyz'
__version__ = '0.2'

user_agent = 'Stock Quotr 0.2 by /u/spookyyz'
r = praw.Reddit(user_agent=user_agent)
r.login(os.environ['REDDIT_USER'], os.environ['REDDIT_PASS'])

cache = []
ticker_symbols = []
ticker_found = 0
symbol = ""
START_TIME = time.time()

class ticker_post(object):

    def yql_name(self, symbol):
        print symbol
        url = "https://query.yahooapis.com/v1/public/yql"
        query = 'select Name from yahoo.finance.quotes where symbol in ("%s")' %symbol
        payload = {'q' : query, 'diagnostics' : 'false', 'env' : 'store://datatables.org/alltableswithkeys', 'format' : 'json'}
        try:
            r = requests.get(url, params=payload)
        except e:
            print "YAHOO LOOKUP ERROR: " + str(e)
        json_response = json.loads(r.text)
        json_quote = json_response["query"]["results"]["quote"]
        company_names = []
        print "YQL: " + str(json_quote)
        for item in json_quote:

            try:
                company_names.append( '[' + str(item['Name']) + ']' + '(http://finance.yahoo.com/q?s=' + symbol + ')') #multiple symbols
            except:
                company_names.append('[' + str(json_quote['Name']) + ']' + '(http://finance.yahoo.com/q?s=' + symbol + ')') # only 1 symbol

        return company_names

    def __init__(self, symbol):
        self.current_price = []
        self.time_of_quote = []
        self.symbol = []
        self.price_change = []
        self.price_change_percent = []
        self.spacer = []
        self.price_info = []
        self.company_names = []
        self.split_symbols = ', '.join(symbol)
        self.company_names = self.yql_name(self.split_symbols)
        data_g = getQuotes(symbol)
        for idx, info in enumerate(data_g):

            #gathering google data
            self.current_price.append(info['LastTradePrice'])
            self.time_of_quote.append("^^as ^^of ^^" + info['LastTradeDateTimeLong'].replace(" ", " ^^"))
            self.symbol.append(info['StockSymbol'])
            self.price_change.append(info['Change'])
            self.price_change_percent.append(info['ChangePercentage'])
            self.price_info.append("**$" + info['LastTradePrice'] + "** *^" + info['Change'] + "* ^*(" + info['ChangePercentage'] + "%)*")
            self.spacer.append('---')

    def post_data(self):
        #build post line by line (for table formatting)
        header_line = "| " + ' | '.join(self.symbol) + " |\r\n"
        spacer_line = "| " + '|'.join(self.spacer) + " |\r\n"
        company_name_line = "| " + ' | '.join(self.company_names) + " |\r\n"
        price_line = "| " + ' | '.join(self.price_info) + " |\r\n"
        date_line = "| " + ' | '.join(self.time_of_quote) + " |\r\n"
        info_line = "\r\n^(_Quotr Bot v%s created by /u/spookyyz ) ^|| ^(Feel free to message me with any ideas or problems_)" % __version__

        self.post = "" + header_line  + spacer_line + company_name_line + "" + price_line + "" + date_line + "" + info_line
        print self.post
        return self.post



def run_bot():
    subreddit = r.get_subreddit('investing')
    for comment in subreddit.get_comments(limit=25): #iterate through 25 most recent comments for symbols
        ticker_symbols = []
        ticker_found=0
        comment_text = comment.body
        pattern = re.compile('\$[A-Z\.]{1,6}')
        comment_utcunix = datetime.datetime.utcfromtimestamp(comment.created) - datetime.timedelta(hours=8) #offset from comment time as seen by the server to UTC
        start_utcunix = datetime.datetime.utcfromtimestamp(START_TIME)
        if (comment.id not in cache and comment_utcunix > start_utcunix): #ignore previously grabbed comments
            for symbol in re.findall(pattern, comment_text): #check for symbol against regex in comment text for non-cached comments
                ticker_symbols.append(symbol[1:])
                ticker_found=1
                ticker_symbols = list(OrderedDict.fromkeys(ticker_symbols))

            if (ticker_found):
                try:
                    cache.append(comment.id)
                    text_to_post = ticker_post(ticker_symbols)
                    post_text = text_to_post.post_data()
                    print "Attempting to reply to " + comment.id + "."
                    comment.reply(post_text)
                    print "Replied to " + comment.id + " successfully.  Sleeping for 5."
                    time.sleep(5)
                except Exception,e:
                    print ("Error posting (possible throttling) response to %s" % comment.id)
                    print "ERROR: " + str(e)
                    cache.pop()
                    print cache
                    time.sleep(5)

                del ticker_symbols[:]

while True:
    run_bot()
    time.sleep(20)
