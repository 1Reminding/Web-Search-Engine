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
def get_expand_urls(bs, url,download_id_counter):
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
        # 如果是下载链接
        index_suffix = href.rfind(".")
        if href[index_suffix + 1:] in download_suffix_list:  # 如果是下载地址
            # 可能从<a>标签获取标题或者描述
            file_title = item.get_text().strip()  # 链接文本作为标题
            if not file_title:
                file_title = "Unknown Title"  # 如果没有链接文本，设为默认标题
            # # 打印下载链接信息，包括序号
            # download_id = len(urls_taken) + 1  # 为每个链接分配一个唯一的序号
            # 打印下载链接信息，包括序号
            download_id = download_id_counter[0]  # 获取当前的下载 ID
            download_id_counter[0] += 1  # 更新 ID 计数器
            logging.info(f"[{download_id}]Download link found: {href}, Title: {file_title}")
            # 获取文件类型
            file_type = href.split('.')[-1] if '.' in href else 'unknown'

            # 保存下载链接信息
            download_info = {
                "url": href,
                "title": file_title,
                "file_type": file_type,
                "file_name": href.split("/")[-1],
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            # with open(os.path.join(dirname, f"download_{download_id}.json"), 'w', encoding="utf-8") as file:
            #     json.dump(download_info, file, ensure_ascii=False)
            # continue

            # 保存每个下载链接为单独的JSON文件
            json_file_name = f"download_{download_id}.json"
            with open(os.path.join(dirname, json_file_name), 'w', encoding="utf-8") as file:
                json.dump(download_info, file, ensure_ascii=False)

            # 这里不用继续执行，也没有必要保存其他链接的信息
            continue  # 一旦保存该链接的json，继续检查下一个链接

        urls_expand.append(href)
    # 如果没有扩展链接，返回空列表而不是 None
    return urls_expand if urls_expand else []

# 保存下载链接到文件
def save_download_links(download_links):
    filename = "download_links.json"
    if os.path.exists(filename):
        with open(filename, 'r', encoding="utf-8") as file:
            all_links = json.load(file)
    else:
        all_links = []

    all_links.extend(download_links)

    with open(filename, 'w', encoding="utf-8") as file:
        json.dump(all_links, file, ensure_ascii=False, indent=4)
    logging.info(f"Saved {len(download_links)} download links.")

# 迭代爬虫
def crawl_loop(i, url_count,  download_link_count, urls_target, urls_taken,download_id_counter, max_crawl_count):
    # 如果已经达到最大深度、迭代次数，或者达到了最大爬取数量，停止爬虫
    if i == 0:
        logging.info("Crawl finished!")
        logging.info(f"Total URLs crawled: {url_count}")
        logging.info(f"Total download links found: {download_link_count}")
        return

    urls_expand = []
    download_links = []

    for url in urls_target:
        html = get_html(url)
        bs = BeautifulSoup(html, "html.parser")
        for url_expand in get_expand_urls(bs, url,download_id_counter):
            if url_expand not in urls_taken:
                html_expand = get_html(url_expand)
                bs_expand = BeautifulSoup(html_expand, "html.parser")
                url_count += 1
                new_links = get_expand_urls(bs_expand, url_expand,download_id_counter)
                if new_links is None:
                    continue  # 如果返回 None，则跳过当前循环

                download_links.extend(new_links)
                download_link_count += len(new_links)
                urls_expand.append(url_expand)
                # 添加到已爬取集合中
                for new_url in new_links:
                    urls_taken.add(new_url)
                #logging.info(f"Total crawled pages: {url_count} - Total download links: {download_link_count}")
        if url_count >= max_crawl_count:  # 如果达到最大爬取数量，跳出外层循环
            break

        # 保存下载链接
    save_download_links(download_links)
    # 递归调用 crawl_loop，继续爬取
    return crawl_loop(i - 1, url_count, download_link_count, urls_expand, urls_taken,download_id_counter, max_crawl_count)

# 爬虫设置和初始化
download_id_counter = [1]  # 初始化下载 ID 计数器
dirname = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")  # 目录名称
os.mkdir(dirname)
crawl_timeout = 1  # 爬虫连接超时时间
crawl_iteration_times = 8  # 爬虫迭代次数
html_index = 0  # 网页索引
url_count = 0  # 总爬取网页数量
urls_target = []  # 爬虫目标网址
#urls_taken = []  # 已访问的网址
urls_taken = set()  # 使用集合来避免重复
urls_invalid = []  # 无效的网址
max_crawl_count = 30000  # 设定最大爬取数量
# 从目标网址文件加载目标网址
with open("default_urls_download.json") as file:
    urls_target = json.load(file)

# 执行爬虫
crawl_loop(crawl_iteration_times, url_count, 0, urls_target, urls_taken,download_id_counter, max_crawl_count)