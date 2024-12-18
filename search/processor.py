# search/processor.py
import math

class ResultProcessor:
    def __init__(self, results_per_page=10):
        self.RESULTS_PER_PAGE = results_per_page
        # #定义要排除的URL列表，短语查询时开启
        # self.EXCLUDED_URLS = [
        #     # 在这里添加更多需要排除的URL
        # ]
    def process_results(self, results, page=1):
        """处理搜索结果并应用分页"""
        # 过滤掉不想显示的URL
        # filtered_results = [hit for hit in results if hit.get('url') not in self.EXCLUDED_URLS]
        # total_results = len(filtered_results)
        #正常查询注释掉上面两句，恢复下面这一句

        total_results = len(results)
        total_pages = math.ceil(total_results / self.RESULTS_PER_PAGE)

        # 计算分页
        start_page = max(1, page - 5)
        end_page = min(total_pages, start_page + 9)
        if end_page - start_page < 9:
            start_page = max(1, end_page - 9)

        # 获取当前页的结果
        start_idx = (page - 1) * self.RESULTS_PER_PAGE
        end_idx = start_idx + self.RESULTS_PER_PAGE
        page_results = results[start_idx:end_idx]
        # 正常查询恢复上面这句，注释下面这一句
        #page_results = filtered_results[start_idx:end_idx]  # 这里使用filtered_results

        # 处理结果
        processed_results = [self._process_single_result(hit) for hit in page_results]

        return {
            'results': processed_results,
            'total': total_results,
            'total_pages': total_pages,
            'page_range': range(start_page, end_page + 1)
        }

    def _process_single_result(self, hit):
        """处理单个搜索结果"""
        # 如果是文档类型，使用特殊的处理方式，不需要处理 content
        if hit.get('filetype'):
            return {
                'title': hit.get('title', '无标题'),
                'filename': hit.get('filename', '未知文件名'),
                'filetype': hit.get('filetype', '未知类型'),
                'upload_date': hit.get('upload_date', None),
                'url': hit.get('url', '#'),  # 如果有文档链接的话
                'snippet': None,  # 文档不显示内容片段
                'source': '',
                'date': '',
                'sort_date': '',
                'snapshot_hash': None,
                'snapshot_date': None
            }

        source = hit.get('source', '')
        date_str = source.split(' - ')[-1] if source else ''
        sort_date = self._process_date(date_str)

        # 特别处理通配符查询的结果
        content = hit.get('content', '')
        highlighted_content = hit.highlights("content")

        if hit.matched_terms():  # 获取匹配的词条
            # 将匹配的词条以及周围的文本包含在snippet中
            snippet = highlighted_content if highlighted_content else content[:200]
        else:
            snippet = content[:200]

        # 从索引中获取快照哈希值和捕获时间
        snapshot_hash = hit.get('snapshot_hash')  # 这个字段在索引中已存储
        captured_at = hit.get('captured_at')  # 这个字段在索引中已存储

        # 格式化快照捕获时间
        snapshot_date = None
        if captured_at:
            try:
                snapshot_date = captured_at.strftime('%Y/%m/%d')
            except:
                snapshot_date = None

        return {
            'title': hit.highlights("title") or hit.get('title', '无标题'),
            'url': hit.get('url', '#'),
            'snippet': snippet,
            'source': hit.get('source', None),
            'date': hit.get('publish_date', None),
            'sort_date': sort_date,
            'filetype': hit.get('filetype', None),
            'filename': hit.get('filename', None),
            'snapshot_hash': snapshot_hash,  # 这个hash用于在数据库中查找对应的快照
            'snapshot_date': snapshot_date   # 显示的快照日期
        }

    def _process_date(self, date_str):
        """处理日期格式"""
        if not date_str:
            return ''
        try:
            parts = date_str.split('-')
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        except:
            return ''