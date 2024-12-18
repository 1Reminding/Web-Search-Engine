from whoosh.index import open_dir
from whoosh.qparser import QueryParser, WildcardPlugin
from whoosh.query import Wildcard
import jieba

# 打开索引
ix = open_dir("index_dir")

# 测试函数
def test_wildcard_patterns():
    with ix.searcher() as searcher:
        # 测试 ? 和 * 的不同情况
        test_cases = [
            "计?",  # 应该匹配："计算"、"计划"等
            "计算*",  # 应该匹配："计算机"、"计算方法"等
            "计*",  # 应该匹配所有以"计"开头的词
            "南开*"  # 应该匹配所有以"南开"开头的词
        ]

        for test_query in test_cases:
            print(f"\n测试查询: {test_query}")

            # 先检查索引中包含的terms
            prefix = test_query.replace('?', '').replace('*', '')
            print(f"索引中包含'{prefix}'开头的terms:")
            matching_terms = []
            for term in searcher.reader().lexicon("content"):
                try:
                    decoded_term = term.decode('utf-8')
                    if decoded_term.startswith(prefix):
                        matching_terms.append(decoded_term)
                except UnicodeDecodeError:
                    continue
            print(f"匹配的terms: {matching_terms[:10]}")  # 只显示前10个

            # 执行查询
            from whoosh.query import Wildcard
            query = Wildcard("content", test_query)
            results = searcher.search(query, limit=5)

            print(f"查询结果数量: {len(results)}")
            for hit in results:
                print(f"- 标题: {hit['title']}")
                print(f"  匹配内容: {hit.highlights('content', top=1)}")

if __name__ == "__main__":
    test_wildcard_patterns()