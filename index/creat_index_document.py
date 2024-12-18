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
        title=TEXT(stored=True, analyzer=analyzer, phrase=True),
        content=TEXT(stored=True, analyzer=analyzer, phrase=True),
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
            'upload_date': doc.get('upload_date') if 'upload_date' in doc else None
        })
        # 打印处理后的 upload_date
        if 'upload_date' in doc:
            print(f"处理后的 upload_date: {doc.get('upload_date')}")

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

    try:
        writer.add_document(**document)
        return True
    except Exception as e:
        print(f"Error adding document {document['id']}: {str(e)}")
        return False


# 4. 初始化索引
def initialize_index():
    if not os.path.exists("index_dir"):
        os.mkdir("index_dir")
    ix = create_in("index_dir", create_schema())

    # 获取所有数据
    collection1_docs, collection2_docs, snapshot_dict, documents = get_mongodb_data()

    # 添加文档到索引
    with ix.writer() as writer:
        doc_count = 0
        news1_count = 0
        news2_count = 0
        print("\n=== 开始处理文档集合(DOCUMENTS) ===")
        # 处理文档
        for doc in documents:
            if add_document(writer, doc, 'document'):
                doc_count  += 1
                if doc_count  % 100 == 0:
                    print(f"已处理 {doc_count } 条数据")

        print("\n=== 开始处理NEWS1集合 ===")
        # 处理NEWS1的文档
        for doc in collection1_docs:
            if add_document(writer, doc, 'format1', snapshot_dict):
                news1_count  += 1
                if news1_count  % 1000 == 0:
                    print(f"已处理 {news1_count } 条数据")

        print("\n=== 开始处理NEWS集合 ===")
        # 处理NEWS的文档
        for doc in collection2_docs:
            if add_document(writer, doc, 'format2', snapshot_dict):
                news2_count += 1
                if news2_count % 1000 == 0:
                    print(f"已处理 {news2_count} 条数据")
    total_count = doc_count + news1_count + news2_count
    print("索引创建完成！共处理 {} 条数据".format(total_count))
    return ix


if __name__ == "__main__":
    ix = initialize_index()