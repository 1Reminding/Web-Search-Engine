# 包含锚文本
# 基础搜索索引
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID, DATETIME, STORED
from jieba.analyse import ChineseAnalyzer
import os
from datetime import datetime
from pymongo import MongoClient
from bs4 import BeautifulSoup

# 1. 连接MongoDB和获取数据
def get_mongodb_data():
    client = MongoClient('localhost', 27017)
    db = client['nankai_news_datasets']  # 替换为您的数据库名

    # 获取网页数据集合1
    collection1 = db['NEWS1']  # 第一种格式的网页数据，无快照
    # 获取网页数据集合2
    collection2 = db['NEWS']  # 第二种格式的网页数据，有快照
    # 获取快照数据
    snapshots = db['WEB_snapshot']  # 快照集合
    # 添加文档集合
    documents = db['DOCUMENTS']  # 假设文档存储在DOCUMENTS集合中
    # 用snapshot_hash创建快照字典，用于NEWS集合
    snapshot_dict = {doc['content_hash']: doc for doc in snapshots.find()}

    # 返回所有数据
    return collection1.find(), collection2.find(), snapshot_dict, documents.find()


# 2. 创建索引结构
def create_schema():
    analyzer = ChineseAnalyzer()
    schema = Schema(
        id=ID(stored=True, unique=True),
        url=ID(stored=True),
        title=TEXT(stored=True, analyzer=analyzer),
        content=TEXT(stored=True, analyzer=analyzer),
        anchor_text=TEXT(stored=True, analyzer=analyzer),  # 添加锚文本字段
        publish_date=DATETIME(stored=True),
        source=TEXT(stored=True),
        snapshot_hash=ID(stored=True),  # 用于匹配对应的快照
        captured_at=DATETIME(stored=True),  # 快照捕获时间

        # 添加文档相关字段
        filetype = ID(stored=True),  # 文档类型(doc/docx/pdf等)
        filename = ID(stored=True),  # 文件名
        upload_date = DATETIME(stored=True)  # 上传时间
    )
    return schema

def extract_anchor_text(html_content):
    """从HTML内容中提取锚文本"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        anchors = soup.find_all('a')
        # 获取所有非空的锚文本
        anchor_texts = [a.get_text().strip() for a in anchors if a.get_text().strip()]
        return " ".join(anchor_texts)
    except Exception as e:
        print(f"Error extracting anchor text: {str(e)}")
        return ""
# 3. 添加文档函数
def add_document(writer, doc, doc_type, snapshot_dict=None):
    document = {
        'id': str(doc['_id']),
        'url': doc['url'] if 'url' in doc else None
    }

    # 处理文档类型
    if 'filetype' in doc:  # 如果是文档
        document.update({
            'filetype': doc['filetype'],
            'filename': doc['filename'] if 'filename' in doc else None,
            'title': doc['title'] if 'title' in doc else None,
            'upload_date': datetime.fromisoformat(doc['upload_date'].replace('Z', '+00:00')) if 'upload_date' in doc else None
        })
        # 可能需要提取文档内容并添加到content字段
        # document['content'] = extract_doc_content(doc)  # 需要实现文档内容提取函数

    # 处理不同格式的数据
    if doc_type == 'format1':  # NEWS1格式，无快照
        if 'title' in doc and doc['title']:
            document['title'] = doc['title']
        if 'content' in doc:
            document['content'] = doc['content']

    elif doc_type == 'format2':  # NEWS格式，有快照
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

        # 只为NEWS格式添加快照信息
        if 'snapshot_hash' in doc:
            document['snapshot_hash'] = doc['snapshot_hash']
            # 从快照集合获取捕获时间
            if snapshot_dict and doc['snapshot_hash'] in snapshot_dict:
                snapshot = snapshot_dict[doc['snapshot_hash']]
                if 'captured_at' in snapshot:
                    document['captured_at'] = snapshot['captured_at']

                # 从快照的HTML内容中提取锚文本
                if 'html_content' in snapshot:
                    anchor_text = extract_anchor_text(snapshot['html_content'])
                    if anchor_text:  # 如果成功提取到锚文本
                        document['anchor_text'] = anchor_text
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
    collection1_docs, collection2_docs, snapshot_dict, documents = get_mongodb_data()

    # 添加文档到索引
    with ix.writer() as writer:
        count = 0

        # 处理文档
        for doc in documents:
            if add_document(writer, doc, 'document'):
                count += 1
                if count % 1000 == 0:
                    print(f"已处理 {count} 条数据")

        # 处理NEWS1的文档
        for doc in collection1_docs:
            if add_document(writer, doc, 'format1', snapshot_dict):
                count += 1
                if count % 1000 == 0:
                    print(f"已处理 {count} 条数据")

        # 处理NEWS的文档
        for doc in collection2_docs:
            if add_document(writer, doc, 'format2', snapshot_dict):
                count += 1
                if count % 1000 == 0:
                    print(f"已处理 {count} 条数据")

    print("索引创建完成！共处理 {} 条数据".format(count))
    return ix


if __name__ == "__main__":
    ix = initialize_index()