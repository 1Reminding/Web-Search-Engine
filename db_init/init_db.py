from pymongo import MongoClient, ASCENDING
from datetime import datetime


def init_user_database():
    """初始化用户相关的所有数据库集合"""
    try:
        # 连接数据库
        client = MongoClient('localhost', 27017)
        db = client['nankai_news_datasets']  # 使用现有的数据库

        # 1. 用户集合 (users)
        if 'users' not in db.list_collection_names():
            users = db.create_collection('users')
            users.create_index([('username', ASCENDING)], unique=True)
            users.create_index([('email', ASCENDING)], unique=True)
            print("用户集合创建成功")

        # 2. 搜索历史集合 (search_history)
        if 'search_history' not in db.list_collection_names():
            search_history = db.create_collection('search_history')
            search_history.create_index([('user_id', ASCENDING)])
            search_history.create_index([('timestamp', ASCENDING)])
            print("搜索历史集合创建成功")

        # 3. 用户偏好设置集合 (user_preferences)
        if 'user_preferences' not in db.list_collection_names():
            preferences = db.create_collection('user_preferences')
            preferences.create_index([('user_id', ASCENDING)], unique=True)
            print("用户偏好集合创建成功")

        # 4. 登录历史集合 (login_history)
        if 'login_history' not in db.list_collection_names():
            login_history = db.create_collection('login_history')
            login_history.create_index([('user_id', ASCENDING)])
            login_history.create_index([('login_time', ASCENDING)])
            print("登录历史集合创建成功")

        print("\n数据库初始化完成！创建了以下集合：")
        print("- users: 用户基本信息")
        print("- search_history: 搜索历史记录")
        print("- user_preferences: 用户偏好设置")
        print("- login_history: 登录历史记录")

        # 展示所有集合的结构
        print("\n各集合的数据结构：")
        print("\nusers 集合结构：")
        print({
            "username": "用户名 (唯一)",
            "email": "邮箱 (唯一)",
            "password": "密码哈希",
            "created_at": "创建时间",
            "last_login": "最后登录时间"
        })

        print("\nsearch_history 集合结构：")
        print({
            "user_id": "用户ID",
            "query": "搜索关键词",
            "search_in": "搜索范围",
            "sort_by": "排序方式",
            "timestamp": "搜索时间"
        })

        print("\nuser_preferences 集合结构：")
        print({
            "user_id": "用户ID",
            "default_search_in": "默认搜索范围",
            "default_sort_by": "默认排序方式",
            "results_per_page": "每页结果数"
        })

        print("\nlogin_history 集合结构：")
        print({
            "user_id": "用户ID",
            "login_time": "登录时间",
            "ip_address": "IP地址"
        })

    except Exception as e:
        print(f"初始化数据库时出错: {str(e)}")
        raise e


if __name__ == "__main__":
    init_user_database()