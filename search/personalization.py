# search/personalization.py
import math
class SearchPersonalization:
    """搜索结果个性化处理类"""

    # 学院相关性映射表
    COLLEGE_RELATIONS = {
        '文学院': ['新闻与传播学院', '汉语言文化学院', '外国语学院'],
        '历史学院': ['文学院', '哲学院', '周恩来政府管理学院'],
        '物理科学学院': ['电子信息与光学工程学院', '材料科学与工程学院'],
        '化学学院': ['材料科学与工程学院', '生命科学学院', '医学院', '药学院'],
        '生命科学学院': ['化学学院', '医学院', '药学院', '环境科学与工程学院'],
        '计算机与网络空间安全学院': ['软件学院', '人工智能学院', '数学科学学院'],
        '计算机学院': ['软件学院', '人工智能学院', '数学科学学院'],  # 兼容简称
        '网络空间安全学院': ['计算机学院', '软件学院', '数学科学学院'],  # 兼容分拆名称
        '数学科学学院': ['统计与数据科学学院', '计算机学院', '人工智能学院'],
        '经济学院': ['商学院', '金融学院', '统计与数据科学学院'],
        '商学院': ['经济学院', '金融学院', '旅游与服务学院'],
        '医学院': ['生命科学学院', '药学院'],
        '周恩来政府管理学院': ['法学院', '马克思主义学院', '历史学院']
    }

    def __init__(self, user_profile=None):
        self.user_profile = user_profile

    def personalize_results(self, results, sort_by='relevance'):
        """
        根据用户身份和排序偏好个性化搜索结果
        Args:
            results: 原始搜索结果列表
            sort_by: 排序方式 ('relevance' 或 'time')
        Returns:
            调整后的搜索结果列表
        """
        if not self.user_profile:
            return results  # 未登录用户返回原始结果

        # 获取用户角色和学院信息
        role = self.user_profile.get('role', '未设置')
        college = self.user_profile.get('college', '未设置')
        # 获取相关学院列表
        related_colleges = self._get_related_colleges(college)

        # 将所有结果转换为(得分,hit)元组列表
        result_list = []
        for hit in results:
            try:
                # 获取或设置基础得分
                base_score = hit.score if hasattr(hit, 'score') else 1.0

                # 安全地获取文档内容
                content = ''
                # 尝试从不同可能的字段获取内容
                content_fields = ['title', 'content', 'text']
                for field in content_fields:
                    if hasattr(hit, field):
                        content += str(getattr(hit, field, '')) + ' '
                    elif hasattr(hit, 'get'):
                        content += str(hit.get(field, '')) + ' '
                content = content.lower()

                # 计算boost因子
                boost = self._calculate_boost(content, role, college, related_colleges)

                # 计算最终得分
                #下面这个算出来有问题，我直接用权重代表final，实验报告用这个
                final_score = boost*(1+0.019*base_score)
                print(base_score)
                print(boost)
                print("final_score的值为:", final_score)
                # 存储元组: (最终得分, 时间戳或默认值, 原始对象)
                timestamp = None
                if hasattr(hit, 'publish_date'):
                    timestamp = getattr(hit, 'publish_date')
                elif hasattr(hit, 'get'):
                    timestamp = hit.get('publish_date')

                result_list.append((final_score, timestamp, hit))

            except Exception as e:
                print(f"处理结果时出错: {str(e)}")
                result_list.append((base_score, None, hit))

        # 根据排序方式排序
        if sort_by == 'time':
            # 先按时间排序，时间相同的按分数排序
            sorted_results = sorted(
                result_list,
                key=lambda x: (x[1] or '', -x[0]),  # 使用空字符串作为默认时间戳
                reverse=True
            )
        else:
            # 按分数排序
            sorted_results = sorted(
                result_list,
                key=lambda x: x[0],  # 使用最终得分排序
                reverse=True
            )

        # 只返回原始对象列表
        return [item[2] for item in sorted_results]

    def _calculate_boost(self, content, role, college, related_colleges):
        """计算搜索结果的权重提升"""
        boost = 1.0
        boost_reasons = []  # 用于记录加分原因

        print(f"\n分析文档: {content[:200]}...")
        print(f"用户角色: {role}, 学院: {college}")

        # 1. 基于角色的内容提升
        if role == '教师':
            if any(tag in content.lower() for tag in ['学术', '科研', '教学', '实验室', '课题']):
                boost *= 1.3
                boost_reasons.append("教师-学术内容匹配: +30%")
            if any(tag in content.lower() for tag in ['教务', '师资', '课程']):
                boost *= 1.2
                boost_reasons.append("教师-教务内容匹配: +20%")
        elif role in ['本科生', '研究生', '博士生']:
            if any(tag in content.lower() for tag in ['学生', '教务', '活动', '奖学金']):
                boost *= 1.2
                boost_reasons.append("学生相关内容匹配: +20%")
            if any(tag in content.lower() for tag in ['就业', '实习', '竞赛', '夜跑', '社团', '活动']):
                boost *= 1.15
                boost_reasons.append("学生活动内容匹配: +15%")

        # 2. 学院相关性判断
        if college != '未设置':
            # 规范化处理内容和学院名称
            normalized_content = content.lower()
            normalized_college = college.lower()

            # 检查文档中是否包含学院名称（包括变体形式）
            college_variations = {
                '计算机与网络空间安全学院': ['计算机学院', '网安学院', '计算机与网安学院', '网络空间安全学院'],
                '文学院': ['文学院', '中文系', '汉语言'],
                '商学院': ['商学院', 'MBA', '工商管理'],
                '医学院': ['医学院', '附属医院', '临床医学'],
                '生命科学学院': ['生科院', '生命学院', '生物学院'],
                '物理科学学院': ['物理学院', '物理系'],
                '化学学院': ['化学院', '化学系'],
                '数学科学学院': ['数学院', '数学系'],
                '经济学院': ['经济系', '经济管理']
            }

            college_matched = False
            # 检查完整学院名称
            if college.lower() in normalized_content:
                boost *= 1.4
                college_matched = True
                boost_reasons.append(f"完整学院名称匹配({college}): +40%")

            # 检查学院变体
            if not college_matched:
                variations = college_variations.get(college, [])
                for variation in variations:
                    if variation.lower() in normalized_content:
                        boost *= 1.3
                        college_matched = True
                        boost_reasons.append(f"学院变体名称匹配({variation}): +30%")
                        break

            # 检查学院关键词
            if not college_matched:
                keywords = self._get_college_context_keywords(college)
                matched_keywords = [kw for kw in keywords if kw.lower() in normalized_content]
                if matched_keywords:
                    keyword_boost = 1.1 + min(len(matched_keywords) * 0.05, 0.3)
                    boost *= keyword_boost
                    boost_reasons.append(
                        f"学院关键词匹配({', '.join(matched_keywords)}): +{(keyword_boost - 1) * 100:.0f}%")

            # 检查相关学院
            for related_college in related_colleges:
                if related_college.lower() in normalized_content:
                    boost *= 1.15
                    boost_reasons.append(f"相关学院匹配({related_college}): +15%")
                    break

            # 检查活动类型和学院组合
            activity_keywords = ['活动', '比赛', '夜跑', '讲座', '社团']
            if any(kw in normalized_content for kw in activity_keywords):
                if college_matched:
                    boost *= 1.25
                    boost_reasons.append("本院活动加分: +25%")
                elif any(related in normalized_content for related in related_colleges):
                    boost *= 1.1
                    boost_reasons.append("相关学院活动加分: +10%")
        #     # 添加PageRank影响
        # try:
        #     # 直接获取pagerank属性
        #     pagerank = getattr(content, 'pagerank', 0)
        #     if pagerank > 0:
        #         # 使用很小的系数确保PageRank不会过度影响排序
        #         pr_boost = 1 + 0.05 * math.log1p(pagerank)
        #         boost *= pr_boost
        #         boost_reasons.append(f"PageRank boost: +{((pr_boost - 1) * 100):.2f}%")
        # except (AttributeError, ValueError) as e:
        #     # 如果无法获取或转换PageRank值，直接忽略
        #     pass
        # 打印加分详情
        print("\n加分详情:")
        for reason in boost_reasons:
            print(f"- {reason}")
        print(f"最终权重系数: {boost:.2f}\n")

        return boost

    def _get_related_colleges(self, college):
        """获取与用户学院相关的其他学院列表"""
        if college == '未设置':
            return []

        # 处理学院名称的不同形式
        college_variants = {
            '计算机与网络空间安全学院': ['计算机学院', '网络空间安全学院', '信息科学学院'],
            '计算机学院': ['计算机与网络空间安全学院', '软件学院', '信息科学学院'],
            '文学院': ['新闻学院', '外国语学院', '汉语言文化学院'],
            '物理科学学院': ['物理学院', '光学工程学院'],
            '化学学院': ['化学系', '材料学院'],
            '医学院': ['生命科学院', '药学院'],
            '商学院': ['经济学院', '管理学院']
        }

        # 获取基础相关学院
        related = self.COLLEGE_RELATIONS.get(college, [])

        # 添加变体形式
        variants = college_variants.get(college, [])

        # 合并所有相关学院，去重
        all_related = list(set(related + variants))

        return all_related

    def _get_college_context_keywords(self, college):
        """获取学院相关的上下文关键词"""
        COLLEGE_KEYWORDS = {
            '计算机与网络空间安全学院': [
                # 专业术语
                '编程', '算法', '软件', '人工智能', '网络',
                '网络安全', '信息安全', '密码学', '渗透测试',
                # 场地
                '实验室', '机房', '创新实践基地',
                # 活动
                '程序设计大赛', '编程竞赛', 'ACM', '网络安全竞赛',
                # 学科
                '计算机科学', '软件工程', '网络工程', '信息安全',
            ],
            '文学院': [
                # 专业术语
                '文学', '写作', '语言', '文化', '古籍',
                # 场地
                '图书馆', '文学社', '创作室',
                # 活动
                '诗歌朗诵', '读书会', '文学讲座', '创作比赛',
                # 学科
                '中国语言文学', '汉语言', '文艺学', '比较文学'
            ],
            '物理科学学院': [
                '物理', '光学', '量子', '实验室', '力学',
                '电磁学', '热学', '光电', '激光'
            ],
            '化学学院': [
                '化学', '分子', '实验', '材料', '有机化学',
                '无机化学', '分析化学', '物理化学'
            ],
            '经济学院': [
                '经济', '金融', '贸易', '市场', '投资',
                '统计', '财务', '商业', '管理'
            ],
            '医学院': [
                '医学', '临床', '病理', '解剖', '生理',
                '药理', '诊断', '治疗', '护理'
            ]
        }

        # 通用关键词
        base_keywords = ['科研', '实验室', '研究', '项目', '讲座', '活动']

        # 获取特定学院的关键词，如果没有则使用空列表
        college_specific = COLLEGE_KEYWORDS.get(college, [])

        # 合并特定关键词和通用关键词
        return college_specific + base_keywords