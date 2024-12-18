import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import networkx as nx


class PageRankHandler:
    def __init__(self):
        self.link_graph = nx.DiGraph()  # 使用有向图存储链接关系

    def add_links(self, from_url, to_urls):
        """添加链接关系到图中"""
        for to_url in to_urls:
            self.link_graph.add_edge(from_url, to_url)

    def calculate_pagerank(self, alpha=0.85):
        """计算PageRank值"""
        return nx.pagerank(self.link_graph, alpha=alpha)

    def save_pagerank(self, pagerank_scores, dirname):
        """保存PageRank结果"""
        with open(os.path.join(dirname, "pagerank.json"), 'w', encoding="utf-8") as f:
            json.dump(pagerank_scores, f, ensure_ascii=False)

    def get_top_pages(self, pagerank_scores, n=10):
        """获取PageRank值最高的n个页面"""
        sorted_pages = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_pages[:n]


# 配置日志
log_filename = datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + "_log.txt"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_filename, mode="w", encoding="utf-8")
    ]
)

# 初始化PageRank处理器
pagerank_handler = PageRankHandler()

# 设置头信息
headers_parameters = {
    'Connection': 'Keep-Alive',
    'Accept': 'text/html',
    'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 下载文档后缀列表
download_suffix_list = [
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "mp3", "mp4", "avi", "mkv", "mov", "wmv", "flv",
    "zip", "rar", "tar", "gz", "bz2", "7z",
    "jpg", "jpeg", "png", "gif", "bmp", "tiff",
    "exe", "apk", "dmg",
    "csv", "txt", "rtf",
    "xls", "xlsx",
]


def get_html(url):
    try:
        response = requests.get(url, timeout=crawl_timeout, headers=headers_parameters, allow_redirects=False)
        response.encoding = response.apparent_encoding
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return ""
    return response.text


def get_expand_urls(bs, url):
    urls_expand = []
    for item in bs.find_all("a"):
        href = item.get("href")
        if href is None:
            continue
        href = str(href)

        # 链接清理和过滤逻辑
        index = href.find("#")
        if index != -1:
            href = href[:index]
        if href.find("javascript") != -1 or href.find("download") != -1:
            continue
        if len(href) < 1 or href == '/':
            continue

        # 处理相对链接
        if href.find("http") == -1:
            if href[0] != '/':
                href = '/' + href
            elif href[0] == '.' and href[1] == '/':
                href = href[1:]
            if url[-1] == '/':
                url = url[:-1]
            href = url + href
        else:
            # 过滤非南开域名链接
            index_of_end_of_domain = href.find('/', href.find("//") + 2)
            index_of_nankai_str = href.find("nankai")
            if index_of_nankai_str == -1 or index_of_nankai_str > index_of_end_of_domain:
                continue

        # 过滤特定URL
        if href.find("less.nankai.edu.cn/public") != -1 or href.find("weekly.nankai.edu.cn/oldrelease.php") != -1:
            continue

        # 过滤下载链接
        index_suffix = href.rfind(".")
        if href[index_suffix + 1:] in download_suffix_list:
            logging.info(f"Download link found: {href}")
            continue

        urls_expand.append(href)

    # 添加链接关系到PageRank处理器
    pagerank_handler.add_links(url, urls_expand)
    return urls_expand


def print_json_data(json_data, html_index):
    logging.info(f"Page {html_index}:")
    logging.info(f"url: {json_data['url']}")
    logging.info(f"title: {json_data['title']}")
    content = json_data["content"]
    content = str(content).replace('\n', '').replace('\t', '')
    logging.info(f"content: {content[:100]}..." if len(content) > 100 else f"content: {content}")


def content_handler(bs, url, index):
    title = ""
    content = ""

    for item in bs.findAll():
        if item.name in ["script", "style"]:
            continue
        content += item.get_text()

    content = re.sub("\n\n", "", content)
    content = content.replace('\n', '').replace('\t', '')

    if bs.title:
        title = bs.title.get_text()

    if not title or any(str(code) in title for code in ["301", "302", "404"]):
        logging.info(f"Skipping page {index} (title: {title})")
        return False

    json_data = {
        "url": url,
        "title": title,
        "content": content,
        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    print_json_data(json_data, index)
    with open(os.path.join(dirname, f"{index}.json"), 'w', encoding="utf-8") as file:
        json.dump(json_data, file, ensure_ascii=False)
    return True


def crawl_loop(i, url_count, html_index, urls_target, urls_taken):
    if i == 0:
        logging.info("Crawl finished!")
        logging.info(f"Total URLs crawled: {url_count}")
        logging.info(f"Total valid URLs: {html_index}")

        # 计算并保存PageRank值
        logging.info("Calculating PageRank...")
        pagerank_scores = pagerank_handler.calculate_pagerank()
        pagerank_handler.save_pagerank(pagerank_scores, dirname)

        # 输出排名靠前的页面
        top_pages = pagerank_handler.get_top_pages(pagerank_scores)
        logging.info("\nTop 10 pages by PageRank:")
        for url, score in top_pages:
            logging.info(f"URL: {url}, PageRank: {score:.6f}")

        logging.info("PageRank calculation completed")
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
                urls_taken.add(url_expand)
                logging.info(f"Total crawled pages: {url_count} - Current page index: {html_index}")

    return crawl_loop(i - 1, url_count, html_index, urls_expand, urls_taken)


# 爬虫设置和初始化
dirname = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
os.mkdir(dirname)
crawl_timeout = 1
crawl_iteration_times = 6
html_index = 0
url_count = 0
urls_target = []
urls_taken = set()

# 从文件加载目标网址
with open("../datasets_and_logs/default_urls.json") as file:
    urls_target = json.load(file)

# 执行爬虫
crawl_loop(crawl_iteration_times, url_count, html_index, urls_target, urls_taken)