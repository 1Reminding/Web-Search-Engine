from pymongo import MongoClient
from datetime import datetime


def test_cleaning_on_sample():
    # 连接MongoDB
    client = MongoClient('mongodb://localhost:27017/')  # 替换成你的MongoDB连接字符串
    db = client['nankai_news_datasets']  # 替换成你的数据库名
    collection = db['NEWS']  # 替换成你的集合名

    # 获取前10条数据的ID
    sample_ids = [doc['_id'] for doc in collection.find().limit(10)]

    print("测试前的数据样本：")
    for doc in collection.find({'_id': {'$in': sample_ids}}):
        print(f"ID: {doc['_id']}")
        print(f"Source: {doc.get('source', '未找到')}")
        print(f"Batch Number: {doc.get('batch_number', '未找到')}")
        print("-" * 50)

    try:
        # 仅对这10条数据进行清洗
        # 清理source字段中的"来源："
        collection.update_many(
            {
                '_id': {'$in': sample_ids},
                'source': {'$regex': '来源：'}
            },
            [{
                '$set': {
                    'source': {
                        '$replaceAll': {
                            'input': '$source',
                            'find': '来源：',
                            'replacement': ''
                        }
                    }
                }
            }]
        )

        # 删除batch_number字段
        collection.update_many(
            {'_id': {'$in': sample_ids}},
            {'$unset': {'batch_number': ''}}
        )

        print("\n清洗后的数据样本：")
        for doc in collection.find({'_id': {'$in': sample_ids}}):
            print(f"ID: {doc['_id']}")
            print(f"Source: {doc.get('source', '未找到')}")
            print(f"Batch Number: {doc.get('batch_number', '未找到')}")
            print("-" * 50)

        user_input = input("\n测试结果是否符合预期？(y/n): ")

        if user_input.lower() == 'y':
            print("\n是否要对所有数据进行清洗？(y/n): ")
            clean_all = input()
            if clean_all.lower() == 'y':
                # 清洗所有数据
                collection.update_many(
                    {'source': {'$regex': '来源：'}},
                    [{
                        '$set': {
                            'source': {
                                '$replaceAll': {
                                    'input': '$source',
                                    'find': '来源：',
                                    'replacement': ''
                                }
                            }
                        }
                    }]
                )

                collection.update_many(
                    {},
                    {'$unset': {'batch_number': ''}}
                )
                print("所有数据清洗完成！")
            else:
                print("操作已取消")
        else:
            print("请调整清洗规则后重试")

    except Exception as e:
        print(f"发生错误: {str(e)}")

    finally:
        client.close()


if __name__ == "__main__":
    test_cleaning_on_sample()