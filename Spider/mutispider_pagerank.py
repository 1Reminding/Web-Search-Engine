import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor
import logging
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from pymongo.operations import UpdateOne
import hashlib
import os
import mimetypes
import gridfs
import numpy as np


class PageRankCalculator:
    def __init__(self, mongo_client):
        self.db = mongo_client['nankai_news_datasets']
        self.news_collection = self.db['NEWS']
        self.links_collection = self.db['LINKS']
        self.pagerank_collection = self.db['PAGERANK']

        # 创建索引
        self.links_collection.create_index([('from_url', 1), ('to_url', 1)], unique=True)
        self.pagerank_collection.create_index([('url', 1)], unique=True)

    def extract_links(self, soup, current_url):
        """提取页面中的所有链接"""
        links = []
        if not soup:
            return links

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href.startswith('/'):
                href = f"http://news.nankai.edu.cn{href}"
            elif not href.startswith('http'):
                continue

            if 'nankai.edu.cn' in href:  # 只保留南开域名下的链接
                links.append({
                    'from_url': current_url,
                    'to_url': href,
                    'anchor_text': a_tag.get_text(strip=True),
                    'created_at': datetime.now()
                })
        return links

    def save_links(self, links):
        """保存链接关系到数据库"""
        if not links:
            return

        for link in links:
            try:
                self.links_collection.update_one(
                    {
                        'from_url': link['from_url'],
                        'to_url': link['to_url']
                    },
                    {'$set': link},
                    upsert=True
                )
            except Exception as e:
                logging.error(f"Error saving link: {str(e)}")

    def build_graph(self):
        """构建网页链接图"""
        graph = {}
        # 获取所有链接关系
        links = self.links_collection.find({})

        for link in links:
            from_url = link['from_url']
            to_url = link['to_url']

            if from_url not in graph:
                graph[from_url] = []
            if to_url not in graph:
                graph[to_url] = []

            if to_url not in graph[from_url]:
                graph[from_url].append(to_url)

        return graph

    def calculate_pagerank(self, damping_factor=0.85, max_iterations=100, min_delta=1e-5):
        """计算PageRank值"""
        graph = self.build_graph()
        if not graph:
            logging.warning("No graph data available for PageRank calculation")
            return {}

        # 初始化PageRank值
        num_pages = len(graph)
        initial_value = 1.0 / num_pages
        pagerank = {url: initial_value for url in graph}

        for iteration in range(max_iterations):
            new_pagerank = {}
            total_diff = 0

            # 计算新的PageRank值
            for url in graph:
                incoming_pr = 0
                for incoming_url in graph:
                    if url in graph[incoming_url]:
                        outgoing_count = len(graph[incoming_url])
                        if outgoing_count > 0:
                            incoming_pr += pagerank[incoming_url] / outgoing_count

                new_value = (1 - damping_factor) / num_pages + damping_factor * incoming_pr
                new_pagerank[url] = new_value
                total_diff += abs(new_value - pagerank[url])

            # 更新PageRank值
            pagerank = new_pagerank

            # 检查是否收敛
            if total_diff < min_delta:
                logging.info(f"PageRank converged after {iteration + 1} iterations")
                break

        return pagerank

    def update_pagerank_scores(self):
        """更新数据库中的PageRank分数"""
        pagerank_scores = self.calculate_pagerank()

        # 批量更新PageRank值
        operations = []
        timestamp = datetime.now()

        for url, score in pagerank_scores.items():
            operations.append(UpdateOne(
                {'url': url},
                {
                    '$set': {
                        'pagerank': score,
                        'updated_at': timestamp
                    }
                },
                upsert=True
            ))

        if operations:
            try:
                result = self.pagerank_collection.bulk_write(operations)
                logging.info(f"Updated {result.modified_count} PageRank scores, "
                             f"Inserted {result.upserted_count} new scores")
            except Exception as e:
                logging.error(f"Error updating PageRank scores: {str(e)}")

    def should_update_pagerank(self, threshold=1000):
        """判断是否需要更新PageRank"""
        last_update = self.pagerank_collection.find_one(
            sort=[('updated_at', -1)]
        )

        if not last_update:
            return True

        # 检查新增链接数量
        new_links_count = self.links_collection.count_documents({
            'created_at': {'$gt': last_update['updated_at']}
        })

        return new_links_count >= threshold


class NewsScraperNankai:
    def __init__(self):
        self.base_url = "http://news.nankai.edu.cn"
        self.first_page = "http://news.nankai.edu.cn/dcxy/index.shtml"
        self.page_template = "https://news.nankai.edu.cn/dcxy/system/count//0005000/000000000000/000/000/c0005000000000000000_000000{:03d}.shtml"
        self.max_pages = 524

        # MongoDB连接设置
        self.mongo_client = MongoClient('mongodb://localhost:27017/')
        self.db = self.mongo_client['nankai_news_datasets']
        self.news_collection = self.db['NEWS']
        self.snapshot_collection = self.db['WEB_snapshot']
        self.fs = gridfs.GridFS(self.db)  # 用于存储附件

        # 创建索引
        self.news_collection.create_index([('url', 1)], unique=True)
        self.snapshot_collection.create_index([('url', 1), ('captured_at', -1)])

        # 初始化PageRank计算器
        self.pagerank_calculator = PageRankCalculator(self.mongo_client)

        # 支持的附件类型
        self.supported_attachments = [
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",  # 常见文档格式
            ".mp3", ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",  # 音频和视频格式
            ".zip", ".rar", ".tar", ".gz", ".bz2", ".7z",  # 压缩文件格式
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",  # 图片格式
            ".exe", ".apk", ".dmg",  # 可执行文件和应用程序
            ".csv", ".txt", ".rtf",  # 文本文件
            ".xls", ".xlsx",  # 表格文件
        ]

        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        }

    def get_page_urls(self):
        """生成所有页面的URL"""
        urls = [self.first_page]  # 第一页
        urls.extend(self.page_template.format(i) for i in range(1, self.max_pages + 1))
        return urls

    def get_soup(self, url, retries=3):
        """获取页面的BeautifulSoup对象和原始HTML内容"""
        for i in range(retries):
            try:
                time.sleep(random.uniform(1, 3))
                response = requests.get(url, headers=self.headers, timeout=10)
                response.encoding = 'utf-8'

                if response.status_code == 200:
                    html_content = response.text
                    return BeautifulSoup(html_content, 'html.parser'), html_content
                else:
                    logging.warning(f"Failed to fetch {url}, status code: {response.status_code}")

            except Exception as e:
                logging.error(f"Attempt {i + 1} failed for {url}: {str(e)}")
                if i == retries - 1:
                    logging.error(f"All attempts failed for {url}")
                    return None, None
                time.sleep(random.uniform(2, 5))
        return None, None

    def save_snapshot(self, url, html_content):
        """保存网页快照"""
        try:
            snapshot_data = {
                'url': url,
                'html_content': html_content,
                'captured_at': datetime.now(),
                'content_hash': hashlib.md5(html_content.encode('utf-8')).hexdigest()
            }
            self.snapshot_collection.insert_one(snapshot_data)
            return snapshot_data['content_hash']
        except Exception as e:
            logging.error(f"Error saving snapshot for {url}: {str(e)}")
            return None

    def find_attachments(self, soup, base_url):
        """查找页面中的附件链接"""
        attachments = []
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if any(ext in href for ext in self.supported_attachments):
                full_url = self.base_url + href if href.startswith('/') else href
                attachments.append({
                    'url': full_url,
                    'filename': os.path.basename(href),
                    'title': link.text.strip()
                })
        return attachments

    def save_attachment(self, attachment_info):
        """保存附件到GridFS"""
        try:
            response = requests.get(attachment_info['url'], headers=self.headers, timeout=30)
            if response.status_code == 200:
                file_id = self.fs.put(
                    response.content,
                    filename=attachment_info['filename'],
                    url=attachment_info['url'],
                    title=attachment_info['title'],
                    upload_date=datetime.now()
                )
                return file_id
        except Exception as e:
            logging.error(f"Error saving attachment {attachment_info['url']}: {str(e)}")
        return None

    def parse_news_list_page(self, url):
        """解析新闻列表页面"""
        soup, html_content = self.get_soup(url)
        if not soup:
            return []

        # 保存列表页快照
        snapshot_hash = self.save_snapshot(url, html_content)

        # 提取并保存页面链接关系
        links = self.pagerank_calculator.extract_links(soup, url)
        self.pagerank_calculator.save_links(links)

        news_items = []
        tables = soup.find_all('table', attrs={'width': "98%", 'border': "0", 'cellpadding': "0", 'cellspacing': "0"})

        for table in tables:
            try:
                title_link = table.find('a')
                if not title_link:
                    continue

                title = title_link.text.strip()
                news_url = self.base_url + title_link['href'] if title_link['href'].startswith('/') else title_link[
                    'href']
                date_td = table.find('td', align="right")
                date = date_td.text.strip() if date_td else None

                logging.info(f"Processing: {title}")

                # 获取新闻详细内容和快照
                article_content, article_snapshot_hash, article_attachments = self.parse_news_detail(news_url)

                news_item = {
                    'title': title,
                    'url': news_url,
                    'date': date,
                    'source': article_content.get('source', ''),
                    'content': article_content.get('content', ''),
                    'snapshot_hash': article_snapshot_hash,
                    'attachments': article_attachments
                }

                news_items.append(news_item)

            except Exception as e:
                logging.error(f"Error parsing news item: {str(e)}")
                continue

        return news_items

    def parse_news_detail(self, url):
        """解析新闻详细页面，包括快照和附件"""
        soup, html_content = self.get_soup(url)
        if not soup:
            return {'source': '', 'content': ''}, None, []

        try:
            # 保存快照
            snapshot_hash = self.save_snapshot(url, html_content)

            # 提取并保存页面链接关系
            links = self.pagerank_calculator.extract_links(soup, url)
            self.pagerank_calculator.save_links(links)

            # 查找附件
            attachments = self.find_attachments(soup, url)
            saved_attachments = []

            # 保存附件
            for attachment in attachments:
                file_id = self.save_attachment(attachment)
                if file_id:
                    saved_attachments.append({
                        'file_id': file_id,
                        'url': attachment['url'],
                        'filename': attachment['filename'],
                        'title': attachment['title']
                    })

            # 解析内容
            source_span = soup.find('span', string=re.compile('来源：'))
            source = source_span.text.strip() if source_span else ''

            content_div = soup.find('td', id='txt')
            if content_div:
                paragraphs = content_div.find_all('p')
                content = '\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])
            else:
                content = ''

            return {
                'source': source,
                'content': content
            }, snapshot_hash, saved_attachments

        except Exception as e:
            logging.error(f"Error parsing detail page {url}: {str(e)}")
            return {'source': '', 'content': ''}, None, []

    def scrape_batch(self, urls, batch_size=10):
        """批量抓取新闻并保存到MongoDB"""
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            batch_number = i // batch_size + 1

            logging.info(f"Processing batch {batch_number}, pages {i + 1} to {min(i + batch_size, len(urls))}")

            # 使用线程池并行处理每批URL
            with ThreadPoolExecutor(max_workers=5) as executor:
                batch_results = list(executor.map(self.parse_news_list_page, batch_urls))

            # 合并结果
            batch_news = [item for sublist in batch_results if sublist for item in sublist]

            # 保存这一批次的数据到MongoDB
            inserted, updated = self.save_to_mongodb(batch_news, batch_number)
            logging.info(f"Batch {batch_number} completed: {inserted} new items, {updated} updates")

            # 检查是否需要更新PageRank
            if self.pagerank_calculator.should_update_pagerank():
                logging.info("Starting PageRank update...")
                self.pagerank_calculator.update_pagerank_scores()
                logging.info("PageRank update completed")

            # 批次间休息
            time.sleep(random.uniform(3, 5))

    def save_to_mongodb(self, news_items, batch_number=None):
        """保存数据到MongoDB"""
        if not news_items:
            logging.warning("No data to save to MongoDB")
            return 0, 0

        inserted_count = 0
        updated_count = 0

        for item in news_items:
            try:
                # 添加时间戳和批次信息
                item['created_at'] = datetime.now()
                item['batch_number'] = batch_number

                # 使用update_one with upsert=True来避免重复插入
                result = self.news_collection.update_one(
                    {'url': item['url']},  # 查询条件
                    {'$set': item},  # 更新的数据
                    upsert=True  # 如果不存在则插入
                )

                if result.upserted_id:
                    inserted_count += 1
                elif result.modified_count:
                    updated_count += 1

            except Exception as e:
                logging.error(f"Error saving to MongoDB: {str(e)}")
                continue

        logging.info(
            f"Batch {batch_number}: Inserted {inserted_count} new documents, Updated {updated_count} documents")
        return inserted_count, updated_count

    def get_news_count(self):
        """获取数据库中的新闻总数"""
        return self.news_collection.count_documents({})

    def update_pagerank_if_needed(self):
        """检查并在需要时更新PageRank"""
        if self.pagerank_calculator.should_update_pagerank():
            logging.info("Starting PageRank update...")
            self.pagerank_calculator.update_pagerank_scores()
            logging.info("PageRank update completed")

    def scrape(self):
        """主抓取函数"""
        logging.info("Starting to scrape news...")
        urls = self.get_page_urls()
        self.scrape_batch(urls)

        # 完成后更新一次PageRank
        self.update_pagerank_if_needed()

        # 打印最终统计信息
        total_news = self.get_news_count()
        logging.info(f"Scraping completed. Total news in database: {total_news}")

def cleanup(self):
    """清理资源"""
    self.mongo_client.close()

def main():
    scraper = None
    try:
        scraper = NewsScraperNankai()
        scraper.scrape()
    except Exception as e:
        logging.error(f"An error occurred during scraping: {str(e)}")
    finally:
        if scraper:
            scraper.cleanup()

if __name__ == "__main__":
    main()