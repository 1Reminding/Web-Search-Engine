from pymongo import MongoClient
import networkx as nx
import numpy as np
from scipy import sparse
from numba import jit
from tqdm import tqdm
import pandas as pd
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import time
from pymongo.operations import UpdateOne
from pymongo.errors import BulkWriteError

class OptimizedPageRankCalculator:
    def __init__(self, damping_factor=0.85, tolerance=1e-6, max_iter=100):
        self.damping_factor = damping_factor
        self.tolerance = tolerance
        self.max_iter = max_iter

        print("初始化数据库连接...")
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['nankai_news_datasets']
        self.collection = self.db['NEWS']
        self.n_jobs = multiprocessing.cpu_count()
        print(f"将使用 {self.n_jobs} 个CPU核心进行计算")

    def build_sparse_matrix(self, urls):
        """构建优化的稀疏矩阵"""
        start_time = time.time()
        n = len(urls)
        print(f"\n第1步/3: 构建稀疏矩阵 (总计 {n} 个URL)")

        # URL映射
        print("创建URL索引映射...")
        url_to_idx = {url: idx for idx, url in enumerate(urls)}

        # 并行处理URL
        chunk_size = max(1000, n // self.n_jobs)
        edges = []

        print("并行构建边关系...")
        with tqdm(total=n) as pbar:
            for i in range(0, n, chunk_size):
                chunk = urls[i:i + chunk_size]
                for url in chunk:
                    parsed = urlparse(url)
                    path = parsed.path.split('/')
                    if len(path) > 2:
                        base = '/'.join(path[:-1])
                        edges.extend([
                            (url_to_idx[url], url_to_idx[other])
                            for other in urls[i:i + chunk_size]
                            if other != url and other.startswith(f"{parsed.scheme}://{parsed.netloc}{base}")
                        ])
                pbar.update(len(chunk))

        # 构建矩阵
        print("构建最终矩阵...")
        # 构建稀疏矩阵
        if edges:
            rows, cols = zip(*edges)
            data = np.ones(len(rows))
            matrix = sparse.csr_matrix((data, (rows, cols)), shape=(n, n))
        else:
            matrix = sparse.csr_matrix((n, n))

        # 标准化矩阵，避免孤立节点
        out_degrees = np.array(matrix.sum(axis=1)).flatten()
        out_degrees[out_degrees == 0] = 1  # 避免除以零
        matrix = sparse.diags(1 / out_degrees) @ matrix

        elapsed = time.time() - start_time
        print(f"矩阵构建完成! 用时: {elapsed:.2f}秒")
        return matrix, url_to_idx

    @staticmethod
    @jit(nopython=True)
    def _power_iteration(matrix_data, matrix_indices, matrix_indptr, damping, n, max_iter, tolerance):
        """使用numba加速的幂迭代"""
        scores = np.full(n, 1.0 / n)  # 初始化为均匀分布
        teleport = (1 - damping) / n

        for iter_num in range(max_iter):
            prev_scores = scores.copy()
            new_scores = np.zeros(n)

            for i in range(n):
                for j in range(matrix_indptr[i], matrix_indptr[i + 1]):
                    col = matrix_indices[j]
                    val = matrix_data[j]
                    new_scores[col] += val * prev_scores[i]

            scores = teleport + damping * new_scores
            diff = np.abs(scores - prev_scores).sum()

            if diff < tolerance:
                break

        return scores, iter_num + 1

    def calculate_pagerank(self):
        """计算PageRank"""
        # 获取所有URL
        print("\n开始PageRank计算...")
        start_time = time.time()

        print("第2步/3: 从数据库加载URL...")
        urls = [doc['url'] for doc in self.collection.find({}, {'url': 1, '_id': 0})]
        n = len(urls)
        print(f"加载完成，共 {n} 个URL")

        # 构建矩阵
        matrix, url_to_idx = self.build_sparse_matrix(urls)

        # 计算PageRank
        print("\n第3步/3: 迭代计算PageRank...")
        scores, iterations = self._power_iteration(
            matrix.data, matrix.indices, matrix.indptr,
            self.damping_factor, len(urls), self.max_iter, self.tolerance
        )

        # 构建结果
        print("整理计算结果...")
        idx_to_url = {v: k for k, v in url_to_idx.items()}
        df = pd.DataFrame({
            'url': [idx_to_url[i] for i in range(len(scores))],
            'pagerank': scores
        })
        df = df.sort_values('pagerank', ascending=False)

        total_time = time.time() - start_time
        print(f"\n计算完成! 总用时: {total_time:.2f}秒")
        print(f"迭代次数: {iterations}")
        return df

    def preview_results(self, df):
        """预览结果"""
        print("\n结果预览:")
        print("\n最高PageRank值的5个页面:")
        for _, row in df.head().iterrows():
            print(f"PageRank: {row['pagerank']:.6e} | URL: {row['url']}")

        print("\n最低PageRank值的5个页面:")
        for _, row in df.tail().iterrows():
            print(f"PageRank: {row['pagerank']:.6e} | URL: {row['url']}")

        stats = df['pagerank'].describe()
        print(f"\n统计信息:")
        print(f"平均值: {stats['mean']:.6e}")
        print(f"标准差: {stats['std']:.6e}")
        print(f"最小值: {stats['min']:.6e}")
        print(f"最大值: {stats['max']:.6e}")

        return input("\n要更新数据库吗？(yes/no): ").lower().strip() == 'yes'

    def update_mongodb(self, df):
        """更新数据库"""
        print("\n开始更新数据库...")
        batch_size = 1000
        total = len(df)
        updated = 0

        with tqdm(total=total, desc="更新进度") as pbar:
            for i in range(0, total, batch_size):
                batch = df.iloc[i:i + batch_size]
                operations = []

                for _, row in batch.iterrows():
                    operations.append(
                        UpdateOne(
                            {'url': row['url']},
                            {'$set': {'pagerank': float(row['pagerank'])}},
                            upsert=False
                        )
                    )

                if operations:
                    try:
                        result = self.collection.bulk_write(operations)
                        updated += result.modified_count
                    except BulkWriteError as bwe:
                        print(f"批量写入错误: {bwe.details}")
                        raise
                pbar.update(len(batch))

        print(f"更新完成! 更新了 {updated} 条记录")

    def run(self):
        """运行主流程"""
        try:
            df = self.calculate_pagerank()
            if self.preview_results(df):
                self.update_mongodb(df)
                print("\n所有操作已完成!")
            else:
                print("\n操作已取消，数据库未更新")
        except Exception as e:
            print(f"发生错误: {str(e)}")


if __name__ == "__main__":
    calculator = OptimizedPageRankCalculator()
    calculator.run()