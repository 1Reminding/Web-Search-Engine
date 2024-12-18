from pymongo import MongoClient
def test_specific_hash(snapshot_hash):
    try:
        client = MongoClient('localhost', 27017)
        db = client['nankai_news_datasets']

        print(f"\n测试特定hash: {snapshot_hash}")

        # 在数据库中查找快照
        snapshot = db.WEB_snapshot.find_one({'content_hash': snapshot_hash})
        if snapshot:
            print("\n1. 找到快照:")
            print(f"- html_content 长度: {len(snapshot.get('html_content', ''))}")
            print(f"- captured_at: {snapshot.get('captured_at')}")
        else:
            print("\n1. 未找到快照")

    except Exception as e:
        print(f"\n错误: {str(e)}")
    finally:
        client.close()


# 测试特定hash
test_specific_hash("ee985e251e6d522d52f10c17d2d283b5")