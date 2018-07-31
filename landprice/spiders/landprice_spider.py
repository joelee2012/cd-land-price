# coding: utf-8
import scrapy
import logging
import re

def strip(s):
    if isinstance(s, (str, bytes)):
        return s.strip()
    return s
    

def price(str):
    if "万元/亩" in str:
        count = re.search('[\d.]+', str).group()
        price = (float(count) * 10000 * 3) / 2000
        return int(price)
    elif "元/平方米" in str:
        return re.search('[\d.]+', str).group()
    else:
        return str
       
            
class LandPriceSpider(scrapy.Spider):
    name = "landprice"
    start_urls = [ "http://www.cdlr.gov.cn/second/zpggg.aspx?ClassID=001002002006001" ]
    headers = { 
            "Host": "www.cdlr.gov.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cookie": "ASP.NET_SessionId=n51a4bvpb2tvjtnyq2j0ig55; zh_choose=n"
            }
    logging.basicConfig(filename="process.log")
    time_pattern = re.compile("时间：(\d+-\d+-\d+)")
    def start_requests(self):
        for url in self.start_urls:
            print(url)
            yield scrapy.Request(url=url, callback=self.parse, headers=self.headers)
            
    def parse(self, response):
        for a in response.xpath("//table/tr/td/a"):
            print(a)
            if "2017" not in a.xpath("@title").extract_first(): continue
            yield response.follow(a, callback=self.parse_detail, errback=self.error_handle)
            
        for next in response.xpath("//div/div/a[13]"):
            if next.xpath("text()").extract_first() == "下一页" and next.xpath("@disabled").extract_first() != "disabled":
                page = re.search(",'(\d+)'", next.xpath("@href").extract_first()).group(1)
                self.logger.info("process page %s", page)
                yield scrapy.FormRequest.from_response(response,
                    formdata={"__EVENTTARGET":"AspNetPager1", "__EVENTARGUMENT":page},         
                    callback=self.parse,
                    errback=self.error_handle,
                    dont_click=True)

            
    def parse_detail(self, response):
        data = {}
        time =  response.xpath("//form/div[1]/div[2]/div[1]/div[3]/text()").extract_first()
        data["发布时间"] = self.time_pattern.search(time).group(1)
        data["网页地址"] = response.url
        data["标题"] = strip(response.xpath("//form/div[1]/div[2]/div[1]/div[1]/text()").extract_first())
        for tr in response.xpath("//div/table/tr"):
            if not tr.xpath("td"): continue
            data["宗地编号"] = strip(tr.xpath("td[2]/text()").extract_first())
            data["宗地位置"] = strip(tr.xpath("td[3]/text()").extract_first())
            data["区域"] = re.match(".*?(市|区|县)", data["宗地位置"]).group()
            data["净用地面积"] = strip(tr.xpath("td[4]/text()").extract_first())
            data["成交价(元/平方米)"] = price(strip(tr.xpath("td[5]/text()").extract_first()))
            data["成交总价(万元)"] = strip(tr.xpath("td[6]/text()").extract_first())
            data["竞得人"] = strip(tr.xpath("td[7]/text()").extract_first())
            yield data
            
    def error_handle(self, failure):
        self.logger.error(repr(failure))
        self.logger.error(failure.request.url)
        