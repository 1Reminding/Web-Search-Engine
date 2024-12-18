# 基础搜索索引
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID, DATETIME, STORED
from jieba.analyse import ChineseAnalyzer
import os
from datetime import datetime
from pymongo import MongoClient


# 1. 连接MongoDB和获取数据
def get_mongodb_data():
    client = MongoClient('localhost', 27017)
    db = client['nankai_news_datasets']  # 替换为您的数据库名

    # 获取网页数据集合1
    collection1 = db['NEWS1']  # 第一种格式的网页数据
    # 获取网页数据集合2
    collection2 = db['NEWS']  # 第二种格式的网页数据
    # 获取快照数据
    snapshots = db['WEB_snapshot']  # 快照集合

    # 创建快照字典用于查找
    snapshot_dict = {doc['_id']: doc for doc in snapshots.find()}

    # 返回所有数据
    return collection1.find(), collection2.find(), snapshot_dict


# 2. 创建索引结构
def create_schema():
    analyzer = ChineseAnalyzer()
    schema = Schema(
        id=ID(stored=True, unique=True),
        url=ID(stored=True),
        title=TEXT(stored=True, analyzer=analyzer),
        content=TEXT(stored=True, analyzer=analyzer),
        publish_date=DATETIME(stored=True),
        source=TEXT(stored=True),
        snapshot_hash=ID(stored=True),
        snapshot_content=STORED  # 存储快照内容但不索引
    )
    return schema


# 3. 添加文档函数
def add_document(writer, doc, doc_type, snapshot_dict=None):
    if 'filename' in doc:  # 跳过文档类型
        return

    document = {
        'id': str(doc['_id']),
        'url': doc['url']
    }

    # 处理不同格式的数据
    if doc_type == 'format1':  # 第一种格式news1
        if 'title' in doc and doc['title']:
            document['title'] = doc['title']
        if 'content' in doc:
            document['content'] = doc['content']
        # 删除对crawl_time的处理

    elif doc_type == 'format2':  # 第二种格式NEWS
        if 'title' in doc and doc['title']:
            document['title'] = doc['title']
        if 'content' in doc:
            document['content'] = doc['content']
        if 'date' in doc:
            try:
                document['publish_date'] = datetime.strptime(doc['date'], "%Y-%m-%d")
            except:
                pass
        if 'source' in doc:
            document['source'] = doc['source']

    # 添加快照信息
    if snapshot_dict and str(doc['_id']) in snapshot_dict:
        snapshot = snapshot_dict[str(doc['_id'])]
        if 'snapshot_hash' in snapshot:
            document['snapshot_hash'] = snapshot['snapshot_hash']
        if 'html_content' in snapshot:
            document['snapshot_content'] = snapshot['html_content']

    try:
        writer.add_document(**document)
        return True
    except Exception as e:
        print(f"Error adding document {document['id']}: {str(e)}")
        return False


# 4. 初始化索引
def initialize_index():
    if not os.path.exists("../index_dir"):
        os.mkdir("../index_dir")
    ix = create_in("index_dir", create_schema())

    # 获取所有数据
    collection1_docs, collection2_docs, snapshot_dict = get_mongodb_data()

    # 添加文档到索引
    with ix.writer() as writer:
        count = 0

        # 处理第一种格式的文档
        for doc in collection1_docs:
            if add_document(writer, doc, 'format1', snapshot_dict):
                count += 1
                if count % 1000 == 0:
                    print(f"已处理 {count} 条数据")

        # 处理第二种格式的文档
        for doc in collection2_docs:
            if add_document(writer, doc, 'format2', snapshot_dict):
                count += 1
                if count % 1000 == 0:
                    print(f"已处理 {count} 条数据")

    print("索引创建完成！共处理 {} 条数据".format(count))
    return ix


if __name__ == "__main__":
    ix = initialize_index()