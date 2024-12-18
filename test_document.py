from whoosh.index import open_dir
from whoosh.query import Term


def get_url_by_id(index_dir, doc_id):
    """
    通过文档ID查询对应的URL

    Args:
        index_dir (str): 索引目录的路径
        doc_id (str): 要查询的文档ID

    Returns:
        str: 文档的URL，如果未找到则返回None
    """
    try:
        # 打开索引目录
        ix = open_dir(index_dir)

        # 创建搜索器
        with ix.searcher() as searcher:
            # 使用Term查询
            query = Term("id", str(doc_id))
            results = searcher.search(query)

            if len(results) > 0:
                # 获取URL
                url = results[0].get('url')
                if url:
                    print(f"文档 ID {doc_id} 的URL是: {url}")
                else:
                    print(f"文档 ID {doc_id} 没有URL信息")
                return url
            else:
                print(f"未找到ID为 {doc_id} 的文档")
                return None

    except Exception as e:
        print(f"查询过程中发生错误: {str(e)}")
        return None


if __name__ == "__main__":
    # 使用示例
    index_dir = "index_dir"  # 索引目录路径
    doc_id = "675bfc1fed10fa8630043272"  # 替换为要查询的文档ID

    # 查询URL
    url = get_url_by_id(index_dir, doc_id)