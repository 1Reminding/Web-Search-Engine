from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId
from whoosh.index import open_dir
from search.manager import SearchManager
from search.processor import ResultProcessor
from search.personalization import SearchPersonalization
from whoosh.query import Or, Term, Prefix
from jieba.analyse import ChineseAnalyzer
from whoosh.scoring import BM25F  # 正确的导入方式
from pypinyin import lazy_pinyin, Style
import re
app = Flask(__name__, static_folder='static')
app.config['JSON_AS_ASCII'] = False
app.secret_key = 'your-secret-key'  # 添加secret key用于session

# 添加这一行配置
# app.config['SESSION_PERMANENT'] = False  # 会话在浏览器关闭时过期

# 设置Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# MongoDB连接
client = MongoClient('localhost', 27017)
db = client['nankai_news_datasets']

RESULTS_PER_PAGE = 10
def format_file_size(size_in_bytes):
    """格式化文件大小"""
    if not isinstance(size_in_bytes, (int, float)) or size_in_bytes < 0:
        return "未知大小"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} PB"
def get_searcher():
    ix = open_dir("index_dir")
    return ix.searcher()

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.created_at = user_data.get('created_at')

    @staticmethod
    def get(user_id):
        user_data = db.users.find_one({'_id': ObjectId(user_id)})
        return User(user_data) if user_data else None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/')
def index():
    return render_template('search.html')

@app.route('/search')
def search():
    # 获取搜索参数
    query = request.args.get('q', '')
    search_type = request.args.get('search_type', 'basic')  # 默认使用基础搜索
    search_in = request.args.get('searchIn', 'all')
    sort_by = request.args.get('sortBy', 'relevance')
    page = int(request.args.get('page', 1))
    filetypes = request.args.getlist('filetypes')  # 获取文件类型列表

    # 记录已登录用户的搜索历史
    if query and current_user.is_authenticated:
        db.search_history.insert_one({
            'user_id': current_user.id,
            'query': query,
            'search_type': search_type,
            'search_in': search_in,
            'sort_by': sort_by,
            'timestamp': datetime.now()
        })

    if not query:
        return render_template('search.html')

    try:
        with get_searcher() as searcher:
            # 使用搜索管理器和结果处理器
            search_manager = SearchManager(searcher, RESULTS_PER_PAGE)
            result_processor = ResultProcessor(RESULTS_PER_PAGE)

            # 执行搜索
            results = search_manager.execute_search(
                search_type,
                query,
                search_in=search_in,
                sort_by=sort_by,
                filetypes=filetypes
            )

            # 进行个性化处理
            final_results = results  # 默认使用原始结果
            if current_user.is_authenticated:
                try:
                    user_profile = db.user_profiles.find_one({'user_id': ObjectId(current_user.id)})
                    if user_profile:
                        # # 为每个搜索结果获取pagerank值
                        # for result in results:
                        #     try:
                        #         # 从URL获取pagerank值
                        #         if hasattr(result, 'url'):
                        #             url = result.url
                        #             # 从数据库中查找对应URL的pagerank值
                        #             page_data = db.NEWS.find_one({'url': url}, {'pagerank': 1})
                        #             if page_data and 'pagerank' in page_data:
                        #                 setattr(result, 'pagerank', float(page_data['pagerank']))
                        #             else:
                        #                 setattr(result, 'pagerank', 0)
                        #     except Exception as e:
                        #         print(f"获取PageRank值错误: {str(e)}")
                        #         setattr(result, 'pagerank', 0)

                        personalizer = SearchPersonalization(user_profile)
                        final_results = personalizer.personalize_results(results, sort_by)
                except Exception as e:
                    print(f"个性化处理错误: {str(e)}")
                    # 如果个性化处理失败，继续使用原始结果
                    pass

            # 使用最终结果进行处理
            processed_data = result_processor.process_results(final_results, page)
            # 如果是文档搜索，格式化文件大小
            if search_type == 'document':
                for result in processed_data['results']:
                    if 'filesize' in result:
                        result['formatted_filesize'] = format_file_size(result['filesize'])
                    if 'upload_date' in result and isinstance(result['upload_date'], datetime):
                        result['formatted_upload_date'] = result['upload_date'].strftime('%Y-%m-%d %H:%M:%S')

            return render_template(
                'search.html',
                query=query,
                search_type=search_type,
                search_in=search_in,
                sort_by=sort_by,
                current_page=page,
                results=processed_data['results'],
                total=processed_data['total'],
                total_pages=processed_data['total_pages'],
                page_range=processed_data['page_range']
            )
    except Exception as e:
        print(f"搜索错误: {str(e)}")
        flash('搜索过程中发生错误，请稍后重试')
        return render_template('search.html')

@app.route('/snapshot/<snapshot_hash>')
def view_snapshot(snapshot_hash):
    try:
        # 从WEB_snapshot集合获取快照内容
        snapshot = db.WEB_snapshot.find_one({'content_hash': snapshot_hash})
        print("Snapshot document:", snapshot)
        if not snapshot:
            flash('未找到网页快照')
            return redirect(url_for('search'))

        # 从NEWS集合获取相关新闻信息
        news = db.NEWS.find_one({'snapshot_hash': snapshot_hash})

        # 准备渲染数据
        render_data = {
            'title': news.get('title', '未知标题') if news else '未知标题',
            'original_url': news.get('url', '#') if news else '#',
            'content': snapshot.get('html_content', ''),
            'captured_time': snapshot.get('captured_at', datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            'source': news.get('source', '') if news else ''
        }

        # 打印调试信息
        print("Snapshot Content Length:", len(render_data['content']) if render_data['content'] else 0)

        return render_template('snapshot.html', **render_data)

    except Exception as e:
        print(f"获取快照错误: {str(e)}")
        flash('获取快照失败')
        return redirect(url_for('search'))

# 以下是用户系统相关路由
@app.route('/login', methods=['POST'])
def login():
    try:
        username = request.form.get('username')
        password = request.form.get('password')

        user_data = db.users.find_one({'username': username})
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)

            # 记录登录历史
            db.login_history.insert_one({
                'user_id': user.id,
                'login_time': datetime.now(),
                'ip_address': request.remote_addr
            })

            # 更新最后登录时间
            db.users.update_one(
                {'_id': ObjectId(user.id)},
                {'$set': {'last_login': datetime.now()}}
            )

            flash('登录成功！')
            return redirect(url_for('index'))

        flash('用户名或密码错误')
    except Exception as e:
        print(f"登录错误: {str(e)}")
        flash('登录过程中发生错误，请稍后重试')
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('两次输入的密码不一致')
            return redirect(url_for('index'))

        if db.users.find_one({'username': username}):
            flash('用户名已存在')
            return redirect(url_for('index'))

        if db.users.find_one({'email': email}):
            flash('邮箱已被注册')
            return redirect(url_for('index'))

        user_data = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'created_at': datetime.now(),
            'last_login': datetime.now()
        }

        # 插入用户基本信息并获取用户ID
        result = db.users.insert_one(user_data)
        user_id = result.inserted_id

        # 创建用户身份信息
        profile_data = {
            "user_id": user_id,
            "role": "未设置",
            "college": "未设置",
            "age": None,
            "created_at": datetime.now(),
            "last_updated": datetime.now()
        }

        # 插入用户身份信息
        db.user_profiles.insert_one(profile_data)

        # 登录用户
        user = User(user_data)
        login_user(user)

        flash('注册成功！')
    except Exception as e:
        print(f"注册错误: {str(e)}")
        flash('注册过程中发生错误，请稍后重试')
    return redirect(url_for('index'))
#个人信息管理功能
@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    """获取当前用户的身份信息"""
    try:
        profile = db.user_profiles.find_one({'user_id': ObjectId(current_user.id)})
        if profile:
            return jsonify({
                'success': True,
                'profile': {
                    'role': profile.get('role', '未设置'),
                    'college': profile.get('college', '未设置'),
                    'age': profile.get('age'),
                    'last_updated': profile.get('last_updated').isoformat() if profile.get('last_updated') else None
                }
            })
        return jsonify({
            'success': False,
            'message': '未找到用户身份信息'
        })
    except Exception as e:
        print(f"获取用户身份信息错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取用户身份信息失败'
        }), 500


@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新用户身份信息"""
    try:
        data = request.get_json()

        # 验证输入数据
        role = data.get('role')
        college = data.get('college')
        age = data.get('age')

        # 验证角色是否合法
        valid_roles = ['本科生', '研究生', '博士生', '教师', '未设置']
        if role and role not in valid_roles:
            return jsonify({
                'success': False,
                'message': '无效的角色类型'
            }), 400

        # 验证年龄是否合法
        if age is not None:
            try:
                age = int(age)
                if age < 0 or age > 120:
                    return jsonify({
                        'success': False,
                        'message': '年龄必须在0-120之间'
                    }), 400
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': '年龄必须是数字'
                }), 400

        # 构建更新数据
        update_data = {
            'last_updated': datetime.now()
        }
        if role is not None:
            update_data['role'] = role
        if college is not None:
            update_data['college'] = college
        if age is not None:
            update_data['age'] = age

        # 更新数据库
        result = db.user_profiles.update_one(
            {'user_id': ObjectId(current_user.id)},
            {'$set': update_data}
        )

        if result.modified_count > 0:
            return jsonify({
                'success': True,
                'message': '身份信息更新成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '未找到用户身份信息或信息未变更'
            })

    except Exception as e:
        print(f"更新用户身份信息错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '更新用户身份信息失败'
        }), 500

#用户相关
#个性化查询用到详细身份信息
@app.route('/profile')
@login_required
def profile_page():
    """渲染用户身份信息页面"""
    try:
        profile = db.user_profiles.find_one({'user_id': ObjectId(current_user.id)})
        return render_template('profile.html', profile=profile)
    except Exception as e:
        print(f"加载个人信息页面错误: {str(e)}")
        flash('加载个人信息页面失败')
        return redirect(url_for('index'))

#个性化推荐——联想搜索
def is_chinese(text):
    """判断是否包含中文字符"""
    return bool(re.search('[\u4e00-\u9fff]', text))

def is_pinyin_or_english(text):
    """判断是否为拼音或英文"""
    return bool(re.match('^[a-zA-Z]+$', text))

def get_pinyin_variations(text):
    """获取拼音变体"""
    # 得到完整的拼音
    full_pinyin = ''.join(lazy_pinyin(text))
    # 得到首字母
    first_letters = ''.join(lazy_pinyin(text, style=Style.FIRST_LETTER))
    return [full_pinyin, first_letters]


@app.route('/api/suggestions')
def get_suggestions():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    try:
        suggestions = []
        seen = set()

        # 获取用户个性化信息
        user_profile = None
        if current_user.is_authenticated:
            user_profile = db.user_profiles.find_one({'user_id': ObjectId(current_user.id)})

        # 1. 从搜索历史获取建议（历史记录优先级最高，保持不变）
        if current_user.is_authenticated:
            regex_pattern = re.compile(f".*{re.escape(query)}.*", re.IGNORECASE)
            historical_queries = db.search_history.find({
                'user_id': current_user.id,
                'query': {'$regex': regex_pattern}
            }).sort('timestamp', -1).limit(5)

            for hist in historical_queries:
                if hist['query'] not in seen:
                    suggestions.append({
                        'text': hist['query'],
                        'type': 'history',
                        'score': 2.0  # 历史记录基础分最高
                    })
                    seen.add(hist['query'])

        # 2. 从索引获取标题建议并应用个性化排序
        with get_searcher() as searcher:
            analyzer = ChineseAnalyzer()
            terms = [token.text for token in analyzer(query)]

            queries = []
            queries.append(Prefix("title", query))
            for term in terms:
                queries.append(Term("title", term))

            q = Or(queries)
            results = searcher.search(q, limit=20)  # 获取更多结果用于排序

            # 计算个性化分数并收集建议
            title_suggestions = []
            for r in results:
                title = r.get('title')
                if title and title not in seen:
                    score = r.score  # 基础相关性分数
                    suggestion = {
                        'text': title,
                        'type': 'title',
                        'score': score  # 初始分数
                    }

                    # 如果用户已登录且有身份信息，应用个性化加权
                    if user_profile:
                        role = user_profile.get('role', '未设置')
                        college = user_profile.get('college', '未设置')

                        # 根据角色加权
                        if role == '教师':
                            if any(tag in title.lower() for tag in ['学术', '科研', '教学', '实验室', '课题']):
                                suggestion['score'] *= 1.3
                            if any(tag in title.lower() for tag in ['教务', '师资', '课程']):
                                suggestion['score'] *= 1.2
                        elif role in ['本科生', '研究生', '博士生']:
                            if any(tag in title.lower() for tag in ['学生', '教务', '奖学金']):
                                suggestion['score'] *= 1.2
                            if any(tag in title.lower() for tag in ['就业', '实习', '竞赛', '社团', '活动']):
                                suggestion['score'] *= 1.15

                        # 根据学院加权
                        if college != '未设置':
                            if college.lower() in title.lower():
                                suggestion['score'] *= 14
                            # 获取相关学院
                            related_colleges = SearchPersonalization.COLLEGE_RELATIONS.get(college, [])
                            for related_college in related_colleges:
                                if related_college.lower() in title.lower():
                                    suggestion['score'] *= 1.15
                                    break

                    title_suggestions.append(suggestion)
                    seen.add(title)

            # 按分数排序标题建议
            title_suggestions.sort(key=lambda x: x['score'], reverse=True)

            # 只保留前10个最相关的建议
            remaining_slots = 10 - len(suggestions)
            suggestions.extend(title_suggestions[:remaining_slots])

        # 最终处理：移除score字段（不需要返回给前端）
        final_suggestions = []
        for suggestion in suggestions:
            final_suggestions.append({
                'text': suggestion['text'],
                'type': suggestion['type']
            })

        return jsonify(final_suggestions)

    except Exception as e:
        print(f"搜索建议错误: {str(e)}")
        return jsonify([]) # 出错时返回空列表而不是抛出异常

#搜索历史相关性和时间衰减策略
# @app.route('/api/suggestions')
# def get_suggestions():
#     query = request.args.get('q', '').strip()
#     if not query:
#         return jsonify([])
#
#     try:
#         all_suggestions = []
#         seen = set()
#
#         # 1. 获取历史记录建议
#         if current_user.is_authenticated:
#             regex_pattern = re.compile(f".*{re.escape(query)}.*", re.IGNORECASE)
#             historical_queries = db.search_history.find({
#                 'user_id': current_user.id,
#                 'query': {'$regex': regex_pattern}
#             }).sort('timestamp', -1)  # 按时间倒序
#
#             for hist in historical_queries:
#                 if hist['query'] not in seen:
#                     # 计算历史记录的匹配度分数
#                     text = hist['query'].lower()
#                     query_lower = query.lower()
#
#                     # 精确匹配得分最高
#                     if text == query_lower:
#                         score = 1000
#                     # 前缀匹配次之
#                     elif text.startswith(query_lower):
#                         score = 800
#                     # 包含匹配再次之
#                     else:
#                         score = 600
#
#                     # 时间衰减：最近7天的记录得分更高
#                     days_old = (datetime.now() - hist['timestamp']).days
#                     if days_old <= 7:
#                         score += (7 - days_old) * 10
#
#                     all_suggestions.append({
#                         'text': hist['query'],
#                         'type': 'history',
#                         'score': score
#                     })
#                     seen.add(hist['query'])
#
#         # 2. 从索引获取标题建议
#         with get_searcher() as searcher:
#             analyzer = ChineseAnalyzer()
#             terms = [token.text for token in analyzer(query)]
#
#             # 构建查询
#             queries = []
#             # 前缀匹配
#             queries.append(Prefix("title", query))
#             # 分词后的词条匹配
#             for term in terms:
#                 queries.append(Term("title", term))
#
#             # 组合查询
#             q = Or(queries)
#             results = searcher.search(q, limit=20)  # 获取更多结果用于排序
#
#             # 处理索引结果
#             for r in results:
#                 title = r.get('title')
#                 if title and title not in seen:
#                     # 计算标题的匹配度分数
#                     text = title.lower()
#                     query_lower = query.lower()
#
#                     # 基础分数：使用 Whoosh 的评分 * 100 作为基础
#                     base_score = r.score * 100
#
#                     # 额外加分项
#                     if text == query_lower:  # 精确匹配
#                         base_score *= 1.5
#                     elif text.startswith(query_lower):  # 前缀匹配
#                         base_score *= 1.3
#
#                     # 长度惩罚：过长的标题适当降低分数
#                     length_penalty = min(1.0, 50 / len(text)) if len(text) > 50 else 1.0
#                     final_score = base_score * length_penalty
#
#                     all_suggestions.append({
#                         'text': title,
#                         'type': 'title',
#                         'score': final_score
#                     })
#                     seen.add(title)
#
#         # 3. 根据分数排序所有建议
#         all_suggestions.sort(key=lambda x: x['score'], reverse=True)
#
#         # 4. 只保留前10个最相关的建议，移除score字段
#         final_suggestions = []
#         for suggestion in all_suggestions[:10]:
#             final_suggestions.append({
#                 'text': suggestion['text'],
#                 'type': suggestion['type']
#             })
#
#         return jsonify(final_suggestions)
#
#     except Exception as e:
#         print(f"搜索建议错误: {str(e)}")
#         return jsonify([])
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已成功退出登录')
    return redirect(url_for('index'))

@app.route('/history')
@login_required
def search_history():
    try:
        history = list(db.search_history.find(
            {'user_id': current_user.id}
        ).sort('timestamp', -1).limit(50))
        return render_template('history.html', history=history)
    except Exception as e:
        print(f"获取历史记录错误: {str(e)}")
        flash('获取搜索历史失败，请稍后重试')
        return redirect(url_for('index'))


@app.route('/api/search_history', methods=['GET'])
@login_required
def get_search_history():
    try:
        # 获取最近10条搜索记录
        history = list(db.search_history.find(
            {'user_id': current_user.id},
            {'query': 1, '_id': 1}
        ).sort('timestamp', -1).limit(10))

        return jsonify({
            'success': True,
            'history': [{'id': str(h['_id']), 'query': h['query']} for h in history]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/search_history/<history_id>', methods=['DELETE'])
@login_required
def delete_search_history(history_id):
    try:
        result = db.search_history.delete_one({
            '_id': ObjectId(history_id),
            'user_id': current_user.id
        })
        return jsonify({'success': True, 'deleted': result.deleted_count > 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/search_history', methods=['DELETE'])
@login_required
def clear_search_history():
    try:
        result = db.search_history.delete_many({'user_id': current_user.id})
        return jsonify({'success': True, 'deleted': result.deleted_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/check_login_status')
def check_login_status():
    if current_user.is_authenticated:
        return jsonify({
            'logged_in': True,
            'username': current_user.username
        })
    return jsonify({
        'logged_in': False
    })

@app.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    """处理用户偏好设置"""
    try:
        # POST 请求 - 处理表单提交
        if request.method == 'POST':
            # 获取表单数据
            default_search_in = request.form.get('default_search_in', 'all')
            default_sort_by = request.form.get('default_sort_by', 'relevance')
            results_per_page = int(request.form.get('results_per_page', 10))

            # 更新数据库中的用户偏好设置
            db.user_preferences.update_one(
                {'user_id': ObjectId(current_user.id)},
                {
                    '$set': {
                        'default_search_in': default_search_in,
                        'default_sort_by': default_sort_by,
                        'results_per_page': results_per_page,
                        'updated_at': datetime.now()
                    }
                },
                upsert=True  # 如果不存在则创建新记录
            )

            flash('设置已更新')
            return redirect(url_for('preferences'))

        # GET 请求 - 显示设置页面
        # 获取当前用户的偏好设置
        user_preferences = db.user_preferences.find_one(
            {'user_id': ObjectId(current_user.id)}
        )

        # 如果没有找到设置，使用默认值
        if not user_preferences:
            user_preferences = {
                'default_search_in': 'all',
                'default_sort_by': 'relevance',
                'results_per_page': 10
            }

        return render_template('preferences.html', preferences=user_preferences)

    except Exception as e:
        print(f"偏好设置错误: {str(e)}")
        flash('操作失败，请稍后重试')
        return redirect(url_for('index'))
# 错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)