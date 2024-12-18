from pymongo import MongoClient, ASCENDING
from datetime import datetime


def init_user_profiles():
    """创建用户身份信息表并为现有用户初始化数据"""
    try:
        # 连接数据库
        client = MongoClient('localhost', 27017)
        db = client['nankai_news_datasets']

        # 1. 创建user_profiles集合
        if 'user_profiles' not in db.list_collection_names():
            user_profiles = db.create_collection('user_profiles')
            # 创建user_id索引确保一个用户只有一个profile
            user_profiles.create_index([('user_id', ASCENDING)], unique=True)
            print("用户身份信息集合创建成功")
        else:
            user_profiles = db['user_profiles']
            print("用户身份信息集合已存在")

        # 2. 获取现有用户列表
        existing_users = db.users.find({}, {'_id': 1})

        # 3. 为现有用户初始化身份信息
        default_profile = {
            "role": "未设置",  # 默认身份
            "college": "未设置",  # 默认学院
            "age": None,  # 默认年龄为空
            "created_at": datetime.now(),
            "last_updated": datetime.now()
        }

        for user in existing_users:
            # 检查用户是否已有profile
            if not user_profiles.find_one({"user_id": user['_id']}):
                profile_data = {
                    "user_id": user['_id'],
                    **default_profile
                }
                user_profiles.insert_one(profile_data)
                print(f"为用户 {user['_id']} 创建默认身份信息")

        print("\n初始化完成！user_profiles集合结构如下：")
        print({
            "user_id": "用户ID (唯一)",
            "role": "身份 (默认'未设置')",
            "college": "学院 (默认'未设置')",
            "age": "年龄 (默认None)",
            "created_at": "创建时间",
            "last_updated": "最后更新时间"
        })

        # 打印初始化统计信息
        total_profiles = user_profiles.count_documents({})
        print(f"\n总计初始化了 {total_profiles} 条用户身份信息")

    except Exception as e:
        print(f"初始化用户身份信息时出错: {str(e)}")
        raise e


def create_profile_for_new_user(user_id):
    """为新注册用户创建身份信息记录"""
    try:
        client = MongoClient('localhost', 27017)
        db = client['nankai_news_datasets']
        user_profiles = db['user_profiles']

        # 检查是否已存在
        if not user_profiles.find_one({"user_id": user_id}):
            profile_data = {
                "user_id": user_id,
                "role": "未设置",
                "college": "未设置",
                "age": None,
                "created_at": datetime.now(),
                "last_updated": datetime.now()
            }
            user_profiles.insert_one(profile_data)
            print(f"为新用户 {user_id} 创建身份信息成功")
        else:
            print(f"用户 {user_id} 的身份信息已存在")

    except Exception as e:
        print(f"创建用户身份信息时出错: {str(e)}")
        raise e


if __name__ == "__main__":
    # 初始化user_profiles集合并为现有用户创建记录
    init_user_profiles()