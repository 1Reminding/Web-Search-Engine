import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging

# 配置日志
log_filename = datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + "_log.txt"  # 日志文件名
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别为INFO，输出INFO及以上级别的日志
    format="%(asctime)s - %(levelname)s - %(message)s",  # 日志格式
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler(log_filename, mode="w", encoding="utf-8")  # 输出到日志文件
    ]
)

# 设置头信息，防止反爬虫
headers_parameters = {
    'Connection': 'Keep-Alive',
    'Accept': 'text/html',
    'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 下载文档后缀列表
download_suffix_list = [
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",  # 常见文档格式
    "mp3", "mp4", "avi", "mkv", "mov", "wmv", "flv",  # 音频和视频格式
    "zip", "rar", "tar", "gz", "bz2", "7z",  # 压缩文件格式
    "jpg", "jpeg", "png", "gif", "bmp", "tiff",  # 图片格式
    "exe", "apk", "dmg",  # 可执行文件和应用程序
    "csv", "txt", "rtf",  # 文本文件
    "xls", "xlsx",  # 表格文件
]

# 获取网页内容
def get_html(url):
    print(url)
    try:
        response = requests.get(url, timeout=crawl_timeout, headers=headers_parameters, allow_redirects=False)
        response.encoding = response.apparent_encoding
    except Exception as e:
        print(e)
        return ""
    return response.text

# 获取网页中的所有链接
def get_expand_urls(bs, url):
    urls_expand = []
    for item in bs.find_all("a"):  # 当前网页html的所有a标签
        href = item.get("href")
        if href is None:
            continue
        href = str(href)
        index = href.find("#")  # 去除#跳转
        if index != -1:
            href = href[:index]
        if href.find("javascript") != -1 or href.find("download") != -1:
            continue
        if len(href) < 1 or href == '/':
            continue
        if href.find("http") == -1:
            if href[0] != '/':
                href = '/' + href
            else:
                if href[0] == '.' and href[1] == '/':
                    href = href[1:]
            if url[-1] == '/':  # 去除url尾部的'/'（如果有）
                url = url[:-1]
            href = url + href
        else:  # 对于绝对地址，直接添加
            index_of_end_of_domain = href.find('/', href.find("//") + 2)
            index_of_nankai_str = href.find("nankai")
            if index_of_nankai_str == -1 or index_of_nankai_str > index_of_end_of_domain:
                continue
        if href.find("less.nankai.edu.cn/public") != -1 or href.find("weekly.nankai.edu.cn/oldrelease.php") != -1:
            continue

        index_suffix = href.rfind(".")
        if href[index_suffix + 1:] in download_suffix_list:  # 如果是下载地址
            logging.info("Download link found: " + href)
            continue

        urls_expand.append(href)
    return urls_expand

# 打印和保存网页数据
def print_json_data(json_data,html_index):
    logging.info(f"Page {html_index}:")
    logging.info("url: " + json_data["url"])
    logging.info("title: " + json_data["title"])
    content = json_data["content"]
    content = str(content).replace('\n', '')
    content = str(content).replace('\t', '')
    if len(content) > 100:
        logging.info("content: " + content[0:99] + "...")
    else:
        logging.info("content: " + content)

# 保存网页内容到文件
def content_handler(bs, url, index):
    title = ""
    content = ""
    for item in bs.findAll():
        if item.name == "script" or item.name == "style":
            continue
        content += item.get_text()
    content = re.sub("\n\n", "", content)
    content = content.replace('\n', '')
    content = content.replace('\t', '')
    if bs.title is not None:
        title = bs.title.get_text()
    if title == "" or title is None or title.find("301") != -1 or title.find("302") != -1 or title.find("404") != -1:
        logging.info(f"Skipping page {index} (title: {title})")  # 打印跳过的页面信息
        return False

    else:
        json_data = {"url": url,
                     "title": title,
                     "content": content,
                     "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        print_json_data(json_data,index)
        with open(os.path.join(dirname, str(index) + ".json"), 'w', encoding="utf-8") as file:
            json.dump(json_data, file, ensure_ascii=False)
        file.close()
        return True

# 迭代爬虫
def crawl_loop(i, url_count, html_index, urls_target, urls_taken):
    if i == 0:
        logging.info("Crawl finished!")
        logging.info(f"Total URLs crawled: {url_count}")
        logging.info(f"Total valid URLs: {html_index}")
        return
    urls_expand = []
    for url in urls_target:
        html = get_html(url)
        bs = BeautifulSoup(html, "html.parser")
        for url_expand in get_expand_urls(bs, url):
            if url_expand not in urls_taken:
                html_expand = get_html(url_expand)
                bs_expand = BeautifulSoup(html_expand, "html.parser")
                url_count += 1
                if not content_handler(bs_expand, url_expand, html_index):
                    continue
                html_index += 1
                urls_expand.append(url_expand)
                # urls_taken.append(url_expand)#对应列表方法
                urls_taken.add(url_expand)  # 修改为 set 的 add 方法
                logging.info(f"Total crawled pages: {url_count} - Current page index: {html_index}")  # 输出当前的爬取数量和页面索引
    return crawl_loop(i - 1, url_count, html_index, urls_expand, urls_taken)

# 爬虫设置和初始化
dirname = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")  # 目录名称
os.mkdir(dirname)
crawl_timeout = 1  # 爬虫连接超时时间
crawl_iteration_times = 6  # 爬虫迭代次数
html_index = 0  # 网页索引
url_count = 0  # 总爬取网页数量
urls_target = []  # 爬虫目标网址
#urls_taken = []  # 已访问的网址
urls_taken = set()  # 使用集合来避免重复
urls_invalid = []  # 无效的网址

# 从目标网址文件加载目标网址
with open("../datasets_and_logs/default_urls.json") as file:
    urls_target = json.load(file)

# 执行爬虫
crawl_loop(crawl_iteration_times, url_count, html_index, urls_target, urls_taken)