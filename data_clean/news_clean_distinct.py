from pymongo import MongoClient
from pprint import pprint


def check_duplicates():
    # 连接MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['nankai_news_datasets']  # 替换成你的数据库名
    collection = db['NEWS']  # 替换成你的集合名

    try:
        # 获取总文档数
        total_docs = collection.count_documents({})
        print(f"\n数据库总文档数量: {total_docs}")

        # 查找重复的URL
        print("\n==== URL重复情况统计 ====")
        duplicate_urls = list(collection.aggregate([
            {
                "$group": {
                    "_id": "$url",
                    "count": {"$sum": 1},
                    "documents": {
                        "$push": {
                            "_id": "$_id",
                            "title": "$title",
                            "source": "$source",
                            "date": "$date"
                        }
                    }
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1}
                }
            },
            {
                "$sort": {"count": -1}  # 按重复次数降序排序
            }
        ]))

        # 打印重复URL的统计信息
        if duplicate_urls:
            print(f"\n发现 {len(duplicate_urls)} 组重复URL")
            total_duplicates = sum(doc['count'] - 1 for doc in duplicate_urls)
            print(f"总共有 {total_duplicates} 条重复文档需要清理")

            # 显示重复文档的详细示例
            print("\n==== 重复文档示例（显示前3组） ====")
            for i, dup in enumerate(duplicate_urls[:3], 1):
                print(f"\n第 {i} 组重复 (重复 {dup['count']} 次):")
                print(f"URL: {dup['_id']}")
                print("包含的文档:")
                for doc in dup['documents']:
                    print("-" * 50)
                    print(f"文档ID: {doc['_id']}")
                    print(f"标题: {doc.get('title', 'N/A')}")
                    print(f"来源: {doc.get('source', 'N/A')}")
                    print(f"日期: {doc.get('date', 'N/A')}")

            # 显示重复次数分布
            print("\n==== 重复次数分布 ====")
            duplicate_counts = {}
            for dup in duplicate_urls:
                count = dup['count']
                duplicate_counts[count] = duplicate_counts.get(count, 0) + 1

            for count, freq in sorted(duplicate_counts.items()):
                print(f"重复 {count} 次的URL有 {freq} 个")

        else:
            print("没有发现重复的URL")

    except Exception as e:
        print(f"检查过程中出错: {str(e)}")
        import traceback
        print(traceback.format_exc())

    finally:
        client.close()


if __name__ == "__main__":
    print("开始检查重复数据...")
    check_duplicates()

    user_input = input("\n是否需要进行数据清理？(y/n): ")
    if user_input.lower() == 'y':
        print("\n请运行清理脚本进行数据清理。")
    else:
        print("操作已取消")