from pymongo import MongoClient
from bson.objectid import ObjectId


def remove_duplicates():
    # 连接MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['nankai_news_datasets']
    collection = db['NEWS1']

    try:
        # 记录清理前的文档数量
        initial_count = collection.count_documents({})
        print(f"清理前文档数量: {initial_count}")

        # 1. 基于URL去重
        print("\n正在基于URL去重...")
        duplicate_urls = collection.aggregate([
            {"$group": {
                "_id": "$url",
                "count": {"$sum": 1},
                "ids": {"$push": "$_id"},
                "first_id": {"$first": "$_id"}
            }},
            {"$match": {
                "count": {"$gt": 1}
            }}
        ], allowDiskUse=True)  # 允许使用磁盘处理大数据集

        url_dups_removed = 0
        for dup in duplicate_urls:
            # 获取要删除的文档ID（除了第一个之外的所有ID）
            ids_to_remove = [id for id in dup["ids"] if id != dup["first_id"]]
            if ids_to_remove:
                result = collection.delete_many({"_id": {"$in": ids_to_remove}})
                url_dups_removed += result.deleted_count
                print(f"删除了 {result.deleted_count} 条URL重复的文档")

        # 2. 基于内容去重
        print("\n正在基于内容去重...")
        duplicate_contents = collection.aggregate([
            {"$group": {
                "_id": "$content",
                "count": {"$sum": 1},
                "ids": {"$push": "$_id"},
                "first_id": {"$first": "$_id"}
            }},
            {"$match": {
                "count": {"$gt": 1}
            }}
        ], allowDiskUse=True)

        content_dups_removed = 0
        for dup in duplicate_contents:
            ids_to_remove = [id for id in dup["ids"] if id != dup["first_id"]]
            if ids_to_remove:
                result = collection.delete_many({"_id": {"$in": ids_to_remove}})
                content_dups_removed += result.deleted_count
                print(f"删除了 {result.deleted_count} 条内容重复的文档")

        # 验证删除结果
        final_count = collection.count_documents({})
        total_removed = initial_count - final_count

        print("\n清理结果统计：")
        print(f"初始文档数量: {initial_count}")
        print(f"最终文档数量: {final_count}")
        print(f"基于URL删除的重复文档: {url_dups_removed}")
        print(f"基于内容删除的重复文档: {content_dups_removed}")
        print(f"实际减少的文档数量: {total_removed}")

        # 显示一个示例文档以确认集合仍然可访问
        print("\n清理后的文档示例：")
        sample = collection.find_one()
        if sample:
            print(f"文档ID: {sample['_id']}")
            print(f"URL: {sample.get('url', 'N/A')}")
            print(f"标题: {sample.get('title', 'N/A')}")
        else:
            print("警告：无法获取示例文档")

    except Exception as e:
        print(f"清理过程中出错: {str(e)}")
        print("错误堆栈:")
        import traceback
        print(traceback.format_exc())

    finally:
        client.close()


if __name__ == "__main__":
    # 确认操作
    print("注意：此操作将直接删除重复文档。建议先备份数据。")
    confirm = input("是否继续？(y/n): ")
    if confirm.lower() == 'y':
        remove_duplicates()
    else:
        print("操作已取消")