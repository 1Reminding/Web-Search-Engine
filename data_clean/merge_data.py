from pymongo import MongoClient
from datetime import datetime


def merge_collections():
    # 连接MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['nankai_news_datasets']  # 替换成你的数据库名

    # 源集合名称
    collection1_name = '2024_11_30_00_52_59'
    collection2_name = '2024_11_30_02_32_56'
    # 目标集合名称（合并后的集合）
    merged_collection_name = 'NEWS1'

    try:
        # 创建一个新的集合来存储合并结果
        if merged_collection_name in db.list_collection_names():
            print(f"集合 {merged_collection_name} 已存在，先删除它")
            db[merged_collection_name].drop()

        # 记录合并前的文档数量
        count1 = db[collection1_name].count_documents({})
        count2 = db[collection2_name].count_documents({})
        print(f"合并前统计:")
        print(f"集合 {collection1_name}: {count1} 条文档")
        print(f"集合 {collection2_name}: {count2} 条文档")

        # 使用聚合管道合并集合
        pipeline = [
            {'$out': merged_collection_name}
        ]

        # 将第一个集合的数据写入新集合
        db[collection1_name].aggregate(pipeline)

        # 将第二个集合的数据添加到新集合
        db[collection2_name].aggregate([
            {'$merge': {
                'into': merged_collection_name,
                'whenMatched': 'keepExisting',  # 如果遇到重复文档，保留已存在的
                'whenNotMatched': 'insert'  # 如果是新文档，则插入
            }}
        ])

        # 统计合并后的文档数量
        merged_count = db[merged_collection_name].count_documents({})
        print(f"\n合并完成！")
        print(f"合并后的集合 {merged_collection_name}: {merged_count} 条文档")

        # 检查是否有重复文档
        if merged_count < count1 + count2:
            print(f"注意：检测到 {count1 + count2 - merged_count} 条重复文档被跳过")

        # 显示合并后的示例文档
        print("\n合并后的文档示例：")
        sample_doc = db[merged_collection_name].find_one()
        print(sample_doc)

    except Exception as e:
        print(f"合并过程中出错: {str(e)}")

    finally:
        client.close()


if __name__ == "__main__":
    merge_collections()