# search/manager.py
from whoosh.qparser import MultifieldParser, QueryParser
from whoosh.query import Term, Or, Phrase, Wildcard, Regex
from whoosh.highlight import ContextFragmenter, HtmlFormatter
from datetime import datetime
import math
from bson.objectid import ObjectId  # 添加这个导入
from pymongo import MongoClient
from whoosh.highlight import ContextFragmenter, HtmlFormatter
class SearchManager:
    def __init__(self, searcher, results_per_page=10):
        self.searcher = searcher
        self.RESULTS_PER_PAGE = results_per_page
        # 定义所有支持的文档类型
        self.SUPPORTED_FILETYPES = ['pdf', 'doc', 'docx', 'xls', 'xlsx']
        # MongoDB 连接
        self.client = MongoClient('localhost', 27017)
        self.db = self.client['nankai_news_datasets']

    def _get_document_info(self, doc_str_id):
        """从MongoDB获取文档详细信息"""
        try:
            # 使用doc_id查询MongoDB获取文件信息
            doc_info = self.db.documents.find_one({'_id': ObjectId(doc_str_id)})
            if doc_info:
                return {
                    'filename': doc_info.get('filename', '未知文件名'),
                    'length': doc_info.get('length', 0),
                    'upload_date': doc_info.get('upload_date')
                }
            return None
        except Exception as e:
            print(f"获取文档信息错误: {str(e)}")
            return None
    def _get_field_config(self, search_in='all'):
        """获取搜索字段和权重配置"""
        if search_in == 'title':
            return {"fields": ["title"], "weights": {"title": 1.0}}
        elif search_in == 'content':
            return {"fields": ["content"], "weights": {"content": 1.0}}
        else:  # 'all'
            return {"fields": ["title", "content"], "weights": {"title": 2.0, "content": 1.0}}

    def execute_search(self, search_type, query_text, search_in='all', sort_by='relevance', filetypes=None):
        """统一的搜索执行接口"""
        field_config = self._get_field_config(search_in)

        # 根据搜索类型选择查询构建方式
        if search_type == 'document':
            query = self._build_document_query(query_text, field_config, filetypes)
            # 执行搜索
            results = self.searcher.search(query, limit=None, terms=True)

            # 只对文档搜索结果添加文件信息
            for hit in results:
                doc_str_id = hit.get('id')
                if doc_str_id:
                    doc_info = self._get_document_info(doc_str_id)
                    if doc_info:
                        hit['filename'] = doc_info['filename']
                        hit['filesize'] = doc_info['length']
                        hit['upload_date'] = doc_info['upload_date']
        elif search_type == 'phrase':
            query = self._build_phrase_query(query_text, field_config)
        elif search_type == 'wildcard':
            query = self._build_wildcard_query(query_text, field_config)
            if query is None:
                # 如果查询无效，返回空结果
                # 如果查询无效，返回空的查询结果，但设置limit为1
                return self.searcher.search(Term("content", "IMPOSSIBLE_MATCH_STRING"), limit=1)
        else:  # basic search
            query = self._build_basic_query(query_text, field_config)

        # 执行搜索
        if sort_by == 'date':
            results = self.searcher.search(
                query,
                limit=None,
                sortedby='publish_date',
                reverse=True,
                terms=True,
            )
        else:
            results = self.searcher.search(query,
                                           limit=None,
                                           terms=True)

        # 设置高亮
        results.fragmenter = ContextFragmenter(maxchars=200, surround=50)
        results.formatter = HtmlFormatter(tagname="strong", classname="highlight")
        results.formatter.between = "..."
        return results

    def _build_basic_query(self, query_text, field_config):
        parser = MultifieldParser(
            field_config["fields"],
            schema=self.searcher.schema,
            fieldboosts=field_config["weights"]
        )
        return parser.parse(query_text)

    def _build_document_query(self, query_text, field_config, filetypes):
        weights = field_config["weights"].copy()
        weights.update({
            "filename": 1.5,
            "filetype": 1.0
        })

        parser = MultifieldParser(
            field_config["fields"] + ["filename", "filetype"],
            schema=self.searcher.schema,
            fieldboosts=weights
        )

        base_query = parser.parse(query_text)

        # 如果用户没有选择文件类型，就使用所有支持的类型
        if not filetypes:
            filetypes = self.SUPPORTED_FILETYPES

        # 构建文件类型过滤器
        filetype_filter = Or([Term("filetype", ft.lower()) for ft in filetypes])
        return base_query & filetype_filter

    def _build_phrase_query(self, query_text, field_config):
        """
        构建短语查询 - 要求精确匹配完整短语
        """
        from whoosh.query import And, Term, Phrase
        from jieba.analyse import ChineseAnalyzer
        # 使用中文分析器进行分词
        analyzer = ChineseAnalyzer()
        terms = [token.text for token in analyzer(query_text)]

        # 如果短语只有一个词，使用 Term 查询
        if len(terms) == 1:
            return Or([Term(field, query_text) for field in field_config["fields"]])

        # 对每个搜索字段构建短语查询
        phrase_queries = []
        for field in field_config["fields"]:
            # 使用 Phrase 查询，slop=0 表示词必须严格相邻
            phrase_queries.append(
                Phrase(field, terms, slop=0)
            )

        # 使用 Or 组合所有字段的查询
        final_query = Or(phrase_queries)

        print(f"构建的短语查询: {final_query}")  # 调试输出
        return final_query

    def _build_wildcard_query(self, query_text, field_config):
        """
        构建通配符查询:
        ? - 匹配单个字符
        * - 匹配零个或多个字符
        """
        from whoosh.query import Or, Wildcard

        def process_query(query):
            # 处理中文通配符
            query = query.replace('？', '?')
            query = query.replace('＊', '*')

            # 关键修改：确保通配符能正确匹配中文
            # 如果查询以*结尾，保持原样；如果不以*结尾且包含*，在*后添加*以匹配任意字符
            if '*' in query and not query.endswith('*'):
                parts = query.split('*')
                query = '*'.join(parts[:-1]) + '*' + parts[-1] + '*'
            elif not '*' in query and not '?' in query:
                query = query + '*'

            return query

        def validate_query(query):
            # 验证通配符使用是否合法
            if not any(char in query for char in ['?', '*']):
                return False
            # 不允许只有通配符的查询
            if query.strip('*?') == '':
                return False
            return True

        queries = []
        fields = field_config["fields"]

        # 处理查询文本
        processed_query = process_query(query_text)
        print(f"处理后的通配符查询: {processed_query}")  # 调试输出

        # 验证查询的合法性
        if not validate_query(processed_query):
            print(f"无效的通配符查询: {query_text}")
            return None

        # 为每个搜索字段创建通配符查询
        for field in fields:
            wildcard = Wildcard(field, processed_query)
            queries.append(wildcard)

        # 组合所有字段的查询
        final_query = Or(queries) if len(queries) > 1 else queries[0]
        print(f"最终通配符查询: {final_query}")  # 调试输出
        return final_query