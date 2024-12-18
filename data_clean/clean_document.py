from pymongo import MongoClient


class MongoDBCleaner:
    def __init__(self, db_name, collection_name):
        # 连接到 MongoDB
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def clean_data(self):
        """清洗数据：删除 chunkSize 字段并添加 filetype 字段"""
        print("开始清洗数据...")

        # 查询所有文档总数
        total = self.collection.count_documents({})  # 获取集合中文档总数
        print(f"总文档数: {total}")

        # 初始化更新计数
        updated = 0

        # 遍历所有文档
        with self.collection.find({}, {'filename': 1}) as cursor:  # 只取需要字段
            for doc in cursor:
                # 提取文件类型
                filetype = None
                if 'filename' in doc:
                    filetype = doc['filename'].split('.')[-1] if '.' in doc['filename'] else 'unknown'

                # 构造更新操作
                update_query = {
                    '$unset': {'chunkSize': ""},  # 删除 chunkSize 字段
                    '$set': {'filetype': filetype}  # 添加 filetype 字段
                }

                # 执行更新
                self.collection.update_one({'_id': doc['_id']}, update_query)
                updated += 1

                # 打印进度（每 100 条打印一次）
                if updated % 100 == 0:
                    print(f"已更新 {updated}/{total} 条记录...")

        print(f"清洗完成！共更新 {updated}/{total} 条记录。")


if __name__ == "__main__":
    # 替换为你的数据库名称和集合名称
    db_name = "nankai_news_datasets"
    collection_name = "Document"

    cleaner = MongoDBCleaner(db_name, collection_name)
    cleaner.clean_data()
