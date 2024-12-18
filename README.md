<h1 align = "center">HW4 - NKU Web Search Engine</h1>

<h5 align = "center">物联网工程 2211999 邢清画</h1>


## 一、项目简介

本项目是基于南开校内资源构建的一个搜索引擎——**ALLINKU**。

![](../img-folder/image-20241217170449292.png)
![image-20241217170449292](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217170449292.png)

- 项目爬取了南开新闻、学术资源、教务、校史、国际合作、校友会、学工会、高等教育研究所、招生办以及各学院的数据总计43万，筛选后进行分配存储在MongoDB中，在10w+数据上用Whoosh库在多个索引域上构建索引。
- 使用Pagerank进行链接分析，评估网页权重。
- 实现了站内查询和文档、短语、通配、网页快照、日志查询五种高级查询。
- 提供用户账号系统，基于用户画像实现个性化查询和推荐。
- 前端采用原生HTML、CSS和JavaScript构建用户界面，并通过Jinja2模板引擎进行页面渲染，利用AJAX技术实现异步加载功能。
- 后端使用Python的Flask框架搭建Web服务器，Flask-Login实现用户认证，MongoDB存储数据，Whoosh用于全文索引，Jieba进行中文分词处理。

PS:ALL-IN-NKU的连写，表示你想找的南开校内资源都可以在这里找到~(￣︶￣)~

## 二、项目概要

### 项目框架

代码结构和主要功能如下图所示：

```
NKU_Web_SearchEngine/
├── ALLINKU/                    # 搜索引擎核心项目
│   ├── index/                 # 索引模块: 负责文档索引的创建和管理
│   ├── index_dir/             # 索引目录: 存储Whoosh生成的索引文件
│   ├── search/                # 搜索模块: 包含搜索管理器、个性化搜索和结果处理
│   │   ├── manager.py          # 搜索管理器: 处理各类搜索请求（基础和高级查询）
│   │   ├── personalization.py # 个性化搜索: 基于用户画像的排序优化
│   │   └── processor.py       # 结果处理器: 处理搜索结果的格式化和分页
│   ├── static/             # 静态资源目录
│   |    └── css/           # CSS样式文件
│   |    	├── main.css    # 主样式
│   |    	├── search.css  # 搜索相关样式
│   |    	├── results.css # 结果呈现样式
│   |    	├── search_history.css  # 搜索历史样式
│   |    	├── user.css    # 用户相关样式
│   |    	├── search_suggestions.css  # 搜索联想（个性化推荐）样式
│   |    	└── pagination.css   # 分页样式
│   ├── templates/          # HTML模板目录
│  	|	├── search.html    # 搜索页面模板
│   |	├── profile.html   # 用户资料页面
│   |	├── history.html   # 搜索历史页面（保存搜索内容、偏好设置、搜索类型和时间等）
│   |	├── preference.html   # 用户偏好设置页面
│   |	└── snapshot.html   # 网页快照页面
│   ├── app.py                 # 主应用入口: Flask应用和路由配置
|	├── test_document.py   # 文档测试模块
|	└── test_wildcard.py   # 通配符搜索测试
├── data_clean/                # 数据清洗模块: 对爬取数据进行预处理
├── datasets_and_logs/         # 数据集和日志: 存储原始数据和系统日志
├── db_init/                   # 数据库初始化: MongoDB数据库初始化脚本
│   ├── init_db_new.py         # 数据库初始化: 用户账号、登录情况、搜索历史等初始化
│   └── init_user_profile.py   # 数据库初始化: 用户详细身份信息初始化
└── Spider/                    # 爬虫模块: 负责网页内容的抓取和更新
	├── downloadlink.py        # 爬虫模块: 专门负责文档的爬取
    ├── htmonly（_pagerank）.py      # 爬虫模块: 专门负责网页的爬取
    └── mutispider（_pagerank）.py   # 爬虫模块: 网页、附带链接、网页快照信息爬取
```

### 1. 系统架构

#### 1.1 前端技术栈

- 原生HTML、CSS、JavaScript构建用户界面
- 基于模板引擎Jinja2进行页面渲染
- 采用AJAX技术实现搜索建议和历史记录的异步加载

#### 1.2 后端技术栈

- Python Flask框架作为Web服务器
- Flask-Login实现用户认证系统
- MongoDB作为主数据库，存储用户信息、搜索历史等
- Whoosh搜索引擎框架用于构建全文索引
- Jieba中文分词器用于中文分词处理

### 2. 核心功能实现

#### 2.1 文档索引系统

- 使用Whoosh构建多域索引(标题、URL、锚文本等)
- 采用ChineseAnalyzer进行中文分词
- BM25F算法用于文档相关性评分

#### 2.2 搜索功能

- 基础搜索：支持普通关键词搜索
- 文档搜索：支持PDF、DOC、DOCX、XLS、XLSX等格式（后面会详细说明）
- 短语搜索：支持精确短语匹配
- 通配符搜索：支持*和?通配符操作
- 网页快照：存储网页历史版本

#### 2.3 个性化功能

- 用户系统：支持注册、登录、个人信息管理
- 搜索历史：记录和展示用户**历史搜索记录**
- 个性化排序：基于用户**角色**(本科生、研究生、教师等)和**院系信息**调整排序权重
- 搜索建议：结合**用户历史**和**实时联想**提供搜索建议

#### 2.4 数据存储设计

- MongoDB集合设计：
  - users：用户基本信息
  - user_profiles：用户身份信息
  - search_history：搜索历史
  - login_history：登录记录
  - NEWS、NEWS1：新闻内容
  - DOCUMENT：各类型文档数据
  - WEB_snapshot：网页快照

### 3. 性能优化

- 使用Redis缓存热门搜索结果
- 采用异步加载优化搜索建议响应速度
- 实现分页机制减少数据传输量

### 4. 技术特色

- 引入PageRank算法进行网页权重计算
- 支持中英文混合搜索
- 实现了基于用户画像的个性化搜索排序

## 三、功能实现

### 3.1 网页抓取

在spider目录下的default_urls.json内设置了多个起始爬取网页链接，包括**南开校史网、新闻网、教务处、各学院、南开大学出版社、校友网、国际研究中心、博士招生、经济研究所、国家重点实验室、陈省身数学研究所、知识产权网等**各大网站。

```
[
    "https://news.nankai.edu.cn", "https://jwc.nankai.edu.cn",
    "https://www.nankai.edu.cn", "https://zsb.nankai.edu.cn",
    "https://lib.nankai.edu.cn","http://international.nankai.edu.cn",
    "https://xgb.nankai.edu.cn","https://law.nankai.edu.cn",
    "http://less.nankai.edu.cn","https://xs.nankai.edu.cn/",
    "https://cc.nankai.edu.cn","https://cs.nankai.edu.cn",
    "https://ai.nankai.edu.cn","https://ceo.nankai.edu.cn",
    "https://finance.nankai.edu.cn","https://math.nankai.edu.cn",
    "https://physics.nankai.edu.cn","https://chem.nankai.edu.cn",
    "https://economics.nankai.edu.cn","https://bs.nankai.edu.cn"
]
```

通过spider中的三个爬虫对网页进行爬取，downloadlink.py（只爬取文档信息链接，用来补充）,htmonly.py（只爬取网页）,mutispider.py（爬取网页和文档信息，保存网页快照）

对爬取完的数据使用data_clean文件下的代码进行数据清洗，包括url去重，时间格式化，补充信息等操作，用于构建索引的数据10w+，下面是MongoDB中各数据集的内容：

**NEWS数据集**（约8w)用来存储网页数据，保存的相关标签信息如图：

![image-20241217172152142](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217172152142.png)

**NEWS1数据集**(约2w筛选后）用来存储网页数据，保存的相关标签信息如图（NEWS1数据需要后处理，去补充更多的信息）：

![image-20241217184922146](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217184922146.png)

![image-20241217184806123](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217184806123.png)

![image-20241217185008968](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217185008968.png)

**网页快照数据集**相关内容WEB_snapshot：

![image-20241217174713138](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217174713138.png)

**文档数据集**（约4000条）相关内容：

![image-20241217175037417](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217175037417.png)

![image-20241217175233504](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217175233504.png)



### 3.2 文本索引——Whoosh

在`index`目录下，使用jieba的ChineseAnalyzer中文分词器对MongoDB中的内容进行分词，并构建Whoosh索引。

由于自身电脑里面的java jdk版本和Elasticsearch自带的版本冲突（且有不可抗因素不能删除我电脑里面的java jdk），选择了使用纯 Python 编写的全文搜索引擎库Whoosh。它提供了用于文本索引和搜索的功能。支持倒排索引，可以高效地对大量文本数据进行搜索。适合在需要内存中存储索引的小型应用中使用。不需要像 Elasticsearch 或 Solr 那样复杂的分布式搜索系统的情况下。常用于本地搜索、文档管理系统、博客搜索等场景。

#### 数据来源

系统从MongoDB数据库中获取以下几类数据：

1. NEWS1集合：包含第一种格式的新闻数据
2. NEWS集合：包含第二种格式的新闻数据，带有网页快照引用
3. WEB_snapshot集合：存储网页快照数据
4. DOCUMENTS集合：存储文档类数据

#### 索引结构设计

使用Whoosh的Schema定义，包含以下字段：

```python
def create_schema():
    analyzer = ChineseAnalyzer()
    schema = Schema(
        # 基础字段：唯一标识和URL
        id=ID(stored=True, unique=True),#唯一标识符（存储）
        url=ID(stored=True),#网页链接（存储）
        
        # 检索内容字段：使用中文分词器，支持短语搜索
        title=TEXT(stored=True, analyzer=analyzer, phrase=True),#标题（存储）
        content=TEXT(stored=True, analyzer=analyzer, phrase=True),#内容（存储）
        
        # 时间和来源字段
        publish_date=DATETIME(stored=True),#发布日期（日期时间类型，存储）
        source=TEXT(stored=True),#来源（存储）
        
        # 快照相关字段
        snapshot_hash=ID(stored=True),#快照哈希值（用于关联快照数据）
        captured_at=DATETIME(stored=True),#快照获取时间
        
        # 文档类型字段
        filetype=ID(stored=True),#文档类型（如doc/docx/pdf等）
        filename=ID(stored=True),#文件名
        upload_date=DATETIME(stored=True)#文档上传时间
    )
    return schema
```

这个结构支持了作业要求中的各类查询功能：

- 全文检索：title、content字段
- 文档查询：filetype、filename字段
- 快照功能：snapshot_hash、captured_at字段
- 时间检索：publish_date、upload_date字段

#### 特殊说明

- 网页快照：没有将快照中的html代码内容构建索引，占空间，可以通过url进入数据库访问，并通过缓存机制优化。
- 日期处理：对日期字段进行标准化处理，统一存储为datetime格式。
- 快照关联：通过snapshot_hash建立NEWS集合与快照数据的关联。
- 数据完整性：对可能缺失的字段进行了空值处理，确保索引构建的稳定性

PS:由于Whoosh本身的特性，我们并不能查看构建完成后的倒排索引。详细代码参见creat_index_document.py

### 3.3 链接分析

完成pagerank算法，并将pagerank评分写入MongoDB，以提升查询服务

#### **链接关系收集** 

首先需要构建网页间的链接图。在爬取过程中，我们提取每个页面中的所有链接，并存储其来源页面和目标页面的关系。

```python
class PageRankHandler:
    def __init__(self):
        self.link_graph = nx.DiGraph()  # 使用有向图存储链接关系

    def add_links(self, from_url, to_urls):
        """添加链接关系到图中"""
        for to_url in to_urls:
            self.link_graph.add_edge(from_url, to_url)

    def calculate_pagerank(self, alpha=0.85):
        """计算PageRank值"""
        return nx.pagerank(self.link_graph, alpha=alpha)

    def save_pagerank(self, pagerank_scores, dirname):
        """保存PageRank结果"""
        with open(os.path.join(dirname, "pagerank.json"), 'w', encoding="utf-8") as f:
            json.dump(pagerank_scores, f, ensure_ascii=False)
```

#### **PageRank计算实现** 

实现PageRank的迭代计算过程。每次迭代中，页面的新PageRank值由两部分组成：

- 随机跳转概率：(1-d)/N，其中d为阻尼因子，N为总页面数
- 链接贡献：所有指向该页面的页面的PageRank值除以它们的出链数量之和

```python
def calculate_pagerank(self, damping_factor=0.85, max_iterations=100):
    """计算PageRank值"""
    graph = self.build_graph()
    num_pages = len(graph)
    pagerank = {url: 1/num_pages for url in graph}  # 初始化
    
    for _ in range(max_iterations):
        new_pagerank = {}
        for url in graph:
            incoming_pr = sum(pagerank[incoming_url] / len(graph[incoming_url])
                            for incoming_url in graph if url in graph[incoming_url])
            new_value = (1-damping_factor)/num_pages + damping_factor * incoming_pr
            new_pagerank[url] = new_value
        pagerank = new_pagerank
    
    return pagerank
```

#### **更新策略设计** 

为了保持PageRank值的时效性，同时避免过于频繁的计算，我们采用增量更新策略：

- 设置链接数量阈值
- 当新增链接数量达到阈值时触发更新
- 爬虫完成后进行一次完整更新

前面代码是**部分内容的简写**，具体完整代码参见项目文件夹下spider文件夹中的代码

最后得到每个网页的pagerank_score并写入MongoDB，示例数据如下：

![image-20241217185208423](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217185208423.png)

#### pagerank值合理性验证：

![image-20241217185558358](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217185558358.png)

- 对于10万条数据来说，PageRank的**总和应接近1**，而平均值理论上应接近 1/100000=1e−5，现在**平均值**为 `1.197831e-05`，接近于理论值，说明结果是合理的。

**PageRank值差异**

- 最大值和最小值的差异约为 1.259478e−05/1.889216e−06≈6.67，这表示权重分布相对均匀，没有极端的高权重页面。
- 在大规模数据集且页面链接较稀疏的情况下，PageRank值分布较窄是正常的，因为链接关系不足以形成显著的权重差异。

**顶端与底端页面**

- 最高PageRank值的页面：都来自同一域（`news.nankai.edu.cn`），而且属于相似的时间路径（2015年3月14日）。这可能表示这些页面之间有较多的互链或外部链接支持它们。
- 最低PageRank值的页面：这些页面属于不同的子路径（`nkzs`, `ntnk`, `dcxy`），时间跨度大且互链较少，权重被稀释。

### 3.4 查询服务

首先打开搜索服务用最广泛涉及到的词检查数据量：

![image-20241217192631920](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217192631920.png)

10W+的数据里约有8w包含关键词，是合理且正确的。

#### 3.4.1 站内查询

用户能在特定网站域名范围内进行内容搜索，本项目只在nankai.edu.cn相关域名下进行搜索

#### 示例结果：

![image-20241217192419633](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217192419633.png)

![image-20241217192259748](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217192259748.png)

#### 关键实现——（代码简化）

- 使用MultifieldParser支持多字段搜索
- 通过field_config配置不同字段的搜索权重

**基本架构：**

```PY
@app.route('/search')
def search():
    query = request.args.get('q', '')  # 获取查询关键词
    search_type = request.args.get('search_type', 'basic')  # 默认使用基础搜索
    search_in = request.args.get('searchIn', 'all')  # 搜索范围
    sort_by = request.args.get('sortBy', 'relevance')  # 排序方式
```

**查询构建(在SearchManager类中):**

```python
def _build_basic_query(self, query_text, field_config):
    parser = MultifieldParser(
        field_config["fields"],
        schema=self.searcher.schema,
        fieldboosts=field_config["weights"]
    )
    return parser.parse(query_text)

def _get_field_config(self, search_in='all'):
    """获取搜索字段和权重配置"""
    if search_in == 'title':
        return {"fields": ["title"], "weights": {"title": 1.0}}
    elif search_in == 'content':
        return {"fields": ["content"], "weights": {"content": 1.0}}
    else:  # 'all'
        return {"fields": ["title", "content"], "weights": {"title": 2.0, "content": 1.0}}
        ......
```

搜索字段权重：标题权重为2.0,内容权重为1.0。这确保了标题匹配的结果会排在前面，可以根据实际需要调整权重，或者增加其他权重。

1. 查询范围：

   ![image-20241217193833186](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217193833186.png)

   - 可以选择只搜索标题(title)
   - 只搜索内容(content)
   - 或者搜索全部(all)

2. 排序支持：

   ![image-20241217193922327](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217193922327.png)

   - 默认按相关度排序(relevance)
   - 可以按日期排序(date)

3. 结果处理：

   - 使用Whoosh的**高亮**功能突出显示匹配的关键词
   - 提取匹配内容的**上下文作为摘要**
   - 支持**分页**显示

#### 3.4.2 文档查询

一些网页可能会携带或其本身就是附件下载链接，支持对文档的查询操作。

#### 示例结果：

不选择文件类型时是搜索全部类型的文档

![image-20241217195003153](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217195003153.png)

选择特定文件类型后会进行筛选（同时也可以选择**搜索范围**和**排序方法**）：
![image-20241217195200393](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217195200393.png)

观察到数量从21减到16，过滤掉了之前不属于筛选条件的文件。

#### 关键实现——(代码简化)

**支持的文档内容**（可扩展，这是爬取时的列表，最终文档类型会包含在其中）：

```python
# 支持的附件类型
self.supported_attachments = [
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",  # 常见文档格式
    ".mp3", ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",  # 音频和视频格式
    ".zip", ".rar", ".tar", ".gz", ".bz2", ".7z",  # 压缩文件格式
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",  # 图片格式
    ".exe", ".apk", ".dmg",  # 可执行文件和应用程序
    ".csv", ".txt", ".rtf",  # 文本文件
    ".xls", ".xlsx",  # 表格文件
]
```

**文档查询构建**：

```python
def _build_document_query(self, query_text, field_config, filetypes):
    weights = field_config["weights"].copy()
    weights.update({
        "filename": 1.5,    # 文件名权重
        "filetype": 1.0     # 文件类型权重
    })

    parser = MultifieldParser(
        field_config["fields"] + ["filename", "filetype"],
        schema=self.searcher.schema,
        fieldboosts=weights
    )

    base_query = parser.parse(query_text)
    # 文件类型过滤
    filetype_filter = Or([Term("filetype", ft.lower()) for ft in filetypes])
    return base_query & filetype_filter
```

**文档信息获取**：

```python
def _get_document_info(self, doc_str_id):
    """从MongoDB获取文档详细信息"""
    try:
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
```

**结果处理特化**：

```PY
def _process_single_result(self, hit):
    """处理单个搜索结果"""
    # 文档类型的特殊处理
    if hit.get('filetype'):
        return {
            'title': hit.get('title', '无标题'),
            'filename': hit.get('filename', '未知文件名'),
            'filetype': hit.get('filetype', '未知类型'),
            'upload_date': hit.get('upload_date', None),
            'url': hit.get('url', '#'),
            'snippet': None,  # 文档不显示内容片段
            'source': '',
            'date': '',
            'sort_date': '',
            'snapshot_hash': None,
            'snapshot_date': None
        }
```

- **多维度搜索：**可以基于**文件名**搜索;支持文件**内容**搜索;可按文件**类型**筛选。
- **权重分配：**文件名**权重**(1.5)高于普通内容；考虑文件类型匹配度(1.0)。
- **结果展示：**显示文件**名**；显示文件**大小**；显示**上传时间**；提供文件**下载链接**。
- **文件类型支持：**定义了支持的文件**类型列表**；可以按文件类型进行**过滤**。

#### 3.4.3 短语查询

支持对多个 Term 的查询

#### 示例效果：

在基础查询功能下搜索“夜跑活动”，选中只筛选标题，看到有五个结果，且其中一个不是精确匹配，剩下的标题中都包含完整且连续的“夜跑活动”：

![image-20241217201947701](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217201947701.png)

接下来打开短语搜索，搜索同样的内容，检查是否还会被搜到：

![image-20241217202328199](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217202328199.png)

看到数量从5减少到4，检查发现含有完整信息的内容都被检索到，原本在第一条的信息不符合精确的短语查询被过滤掉。

#### 关键实现——（代码简化）

调整 slop 参数来控制词语之间允许的距离，并添加一个参数来控制匹配的严格程度。（如slop=0表示严格相邻）

1. 在SearchManager类中的execute_search方法中处理短语查询：

```py
def execute_search(self, search_type, query_text, search_in='all', sort_by='relevance', filetypes=None, strict_mode=False):
    """
    执行搜索的主方法  
    Parameters:
        search_type (str): 搜索类型
        query_text (str): 查询文本
        search_in (str): 搜索范围
        sort_by (str): 排序方式
        filetypes (list): 文件类型列表
        strict_mode (bool): 是否使用严格匹配模式
    """
    field_config = self._get_field_config(search_in)
    
    if search_type == 'phrase':
        query = self._build_phrase_query(query_text, field_config, strict_mode)
```

2. 核心实现方法_build_phrase_query：

```py
def _build_phrase_query(self, query_text, field_config, strict_mode=False):
    """
    构建增强的短语查询，支持不同的匹配模式    
    Parameters:
        query_text (str): 用户输入的查询文本
        field_config (dict): 搜索字段配置
        strict_mode (bool): 是否使用严格匹配模式，默认为False
        
    Returns:
        whoosh.query.Query: 构建的查询对象
    """
    # 使用中文分析器进行分词
    analyzer = ChineseAnalyzer()
    terms = [token.text for token in analyzer(query_text)]
    
    # 如果短语只有一个词，使用 Term 查询
    if len(terms) == 1:
        return Or([Term(field, query_text) for field in field_config["fields"]])
    
    # 根据短语长度动态调整 slop 值
    if strict_mode:
        # 严格模式：要求词语严格相邻
        base_slop = 0
    else:
        # 非严格模式：允许词语之间有一定距离
        # 短语越长，允许的间距越大
        base_slop = min(5, len(terms) - 1)  # 最大允许5个词的间距
    
    # 对每个搜索字段构建短语查询
    phrase_queries = []
    for field in field_config["fields"]:
        # 构建不同松散度的短语查询
        if strict_mode:
            # 严格模式只构建一个严格匹配的查询
            phrase_queries.append(
                Phrase(field, terms, slop=base_slop)
            )
        else:
            # 非严格模式构建多个不同松散度的查询
            # 使用不同的slop值，给予不同的权重
            queries_for_field = [
                Phrase(field, terms, slop=base_slop, boost=1.5),          # 较严格匹配
                Phrase(field, terms, slop=base_slop * 2, boost=1.0),      # 中等匹配
                Phrase(field, terms, slop=base_slop * 3, boost=0.5)       # 松散匹配
            ]
            # 组合同一字段的不同松散度查询
            phrase_queries.extend(queries_for_field)
    
    # 使用 Or 组合所有查询
    final_query = Or(phrase_queries)
    
    # 添加调试输出
    print(f"构建的短语查询: {final_query}")
    return final_query

```

- **保持对原有严格匹配需求的支持（精确的短语匹配，最终使用的方法）**
- 找到词序稍有变化的相关结果（非严格）
- 处理词语之间可能包含其他词的情况（非严格）
- 通过权重机制确保更相关的结果排在前面（非严格）

#### 3.4.4 通配查询

通配符查询允许用户使用特殊字符（`?` 和 `*`等）来进行模糊匹配搜索：

- `?` 匹配任意单个字符
- `*` 匹配零个或多个字

#### 示例结果：

为了体现区别，我们使用李？和李*进行测试，保持搜索和筛选、排序选择一致，不切换账号保证不会受到个性化相关功能影响排序：

![image-20241217205341225](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217205341225.png)

![image-20241217205153730](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217205153730.png)

可以观察到在使用李*之后，查询到了三个字的名字可以匹配。

#### 关键实现——代码简化

1. 通配符查询的核心实现位于 `SearchManager` 类中的 `_build_wildcard_query` 方法：

```py
def _build_wildcard_query(self, query_text, field_config):
    """
    构建通配符查询:
    ? - 匹配单个字符
    * - 匹配零个或多个字符
    """
    def process_query(query):
        # 处理中文通配符
        query = query.replace('？', '?')
        query = query.replace('＊', '*')

        # 如果查询以*结尾，保持原样
        # 如果不以*结尾且包含*，在*后添加*以匹配任意字符
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
    # 验证查询的合法性
    if not validate_query(processed_query):
        return None
    # 为每个搜索字段创建通配符查询
    for field in fields:
        wildcard = Wildcard(field, processed_query)
        queries.append(wildcard)
    # 组合所有字段的查询
    final_query = Or(queries) if len(queries) > 1 else queries[0]
    return final_query
```

**通配符处理**

- 支持中文通配符（？和＊）转换为英文通配符（? 和 *）
- 自动补全功能：如果查询中没有通配符，自动在末尾添加 *
- 智能处理 * 号：确保通配符能正确匹配中文字符

**查询验证**：验证通配符使用的合法性；防止纯通配符查询（如：***）；确保查询包含实际搜索内容。

**多字段搜索**：支持在多个字段（如标题、内容等）中进行通配符搜索；使用 Or 操作符组合多字段查询。

#### 3.4.5 查询日志

在MongoDB中绑定了用户的账号信息，包含用户的偏好设置、详细身份信息、搜索历史、登录时间等。

概览（主界面是搜索历史）：

![image-20241217210435856](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217210435856.png)

用户注册信息：

![image-20241217210643902](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217210643902.png)

详细身份信息（默认可以不填，也可以进入**完善个人信息**模块填写，便于个性化功能的精准实现）：

![image-20241217210524271](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217210524271.png)

登录历史：

![image-20241217210942244](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217210942244.png)

#### 搜索历史表单

其中**搜索历史表单**中显示了每次搜索的内容、搜索的范围（全部、仅标题、仅内容）、排序方式（相关度、时间）、搜索时的时间。

![image-20241217205927444](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217205927444.png)

#### 查询日志主界面显示

切换不同的用户进入到界面点击搜索框未输入时可以显示用户曾经的搜索历史，同时和用户表单中的“搜索历史”模块绑定，在主界面只显示十条，点击查看更多可以跳转至history.html模块（也就是从下拉菜单进入到搜索历史板块）查看所有搜索历史：

![image-20241217210224984](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217210224984.png)

点击搜索框显示不同用户的查询日志：

![image-20241217211441465](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217211441465.png)

切换用户（看时间是之前的搜索记录）：
![image-20241217211645716](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217211645716.png)

点击搜索历史表单

![image-20241217211724777](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217211724777.png)

#### 3.4.6 网页快照

网页快照功能，使用户能够查看历史网页内容，即使原始网页已经发生变化或无法访问。

#### 示例结果：

主搜索界面：

![image-20241217212505606](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217212505606.png)

点击网页快照（这里点击第一个）：

![image-20241217212805264](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217212805264.png)

#### 关键实现——代码简化

1. 使用MongoDB数据库存储快照数据，主要涉及两个集合：

- WEB_snapshot：存储网页快照的具体内容
- NEWS：存储新闻元数据及关联的快照信息

```py
快照文档结构：
{
    'content_hash': String,  # 快照内容的唯一标识
    'html_content': String,  # 网页快照的HTML内容
    'captured_at': DateTime  # 快照捕获时间
}

新闻文档结构：
{
    'title': String,        # 新闻标题
    'url': String,          # 原始URL
    'snapshot_hash': String, # 关联的快照哈希值
    'source': String        # 新闻来源
}
```

因此需要将这两个数据库内容建立联系，才能通过NEWS数据集中的snapshot_hash字段对应到WEB_snapshot数据集中的content_hash字段，然后提取WEB_snapshot数据集中在之前访问网页时，保存的网页HTML内容，呈现在浏览器上，就是在当时访问时的网页快照。

2. **数据组织**：

- 将快照内容和元数据组织成统一的render_data
- 处理可能缺失的字段，提供默认值

```py
@app.route('/snapshot/<snapshot_hash>')
def view_snapshot(snapshot_hash):
    try:
        # 从WEB_snapshot集合获取快照内容
        snapshot = db.WEB_snapshot.find_one({'content_hash': snapshot_hash})
        
        # 获取关联的新闻信息
        news = db.NEWS.find_one({'snapshot_hash': snapshot_hash})
        
        # 准备渲染数据
        render_data = {
            'title': news.get('title', '未知标题') if news else '未知标题',
            'original_url': news.get('url', '#') if news else '#',
            'content': snapshot.get('html_content', ''),
            'captured_time': snapshot.get('captured_at', datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            'source': news.get('source', '')
        }
        
        return render_template('snapshot.html', **render_data)
    except Exception as e:
        print(f"获取快照错误: {str(e)}")
        flash('获取快照失败')
        return redirect(url_for('search'))
```

3. **路径处理**：

- 自动修正快照中的相对路径链接和图片，确保资源能够正确加载和显示。

```JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const originalUrl = "{{ original_url }}";
    const baseUrl = new URL(originalUrl).origin;

    // 处理相对路径链接
    const links = document.getElementsByTagName('a');
    for(let link of links) {
        if(link.href && link.href.startsWith('/')) {
            link.href = baseUrl + link.href;
        }
    }

    // 处理相对路径图片
    const images = document.getElementsByTagName('img');
    for(let img of images) {
        if(img.src && img.src.startsWith('/')) {
            img.src = baseUrl + img.src;
        }
    }
});
```

保持了原始网页的排版和样式；提供了清晰的导航和meta信息；解决了资源路径的问题；实现了响应式布局，适配不同设备。

### 3.5 个性化查询

个性化查询的核心目标是根据用户的**身份特征**（如角色、所属学院）对搜索结果进行重新排序，使得更符合用户兴趣和需求的内容优先展示。实现思路包括：

1. 用户系统设计：实现基础的用户注册、登录功能，并存储用户的身份信息，用户可以在注册之后进行完善，不填写则为默认值。
2. 个性化权重计算：基于用户身份特征对搜索结果进行评分调整
3. 结果重排序：根据调整后的分数对搜索结果进行重新排序

#### 示例结果：

检查不同身份和学院对于同一搜索结果的返回排序：

首先完善用户信息，在主界面用户的下拉菜单选择**完善个人信息**选项：

![image-20241217220410027](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217220410027.png)

进入个人信息表单，选择不同的身份和所属学院（在代码中给学院和学院相关的活动给予了较大的权重）：

![image-20241217220109997](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217220109997.png)

![image-20241217220232016](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217220232016.png)

MongoDB同步更新了user_profiles内容：

![image-20241217220710450](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217220710450.png)

使用**计网本科生**的身份去搜索“夜跑活动”：

![image-20241217221818883](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217221818883.png)

以**金融教师**的身份去搜索“夜跑活动”：

![image-20241217221306764](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217221306764.png)

我们来观察一下终端输出的部分检查点（没显示完全加分策略，这里只用来突出身份对于搜索结果的影响：

学生和教师身份会有对应的关键词设置（可扩展），学院会有相关的名称、学院相关活动的关键词设置（可扩展）

计算机本科生：

![image-20241217222258357](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217222258357.png)

金融教师：

![image-20241217221619006](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217221619006.png)

#### 关键实现——代码简化

##### 1. 用户身份信息管理

用户身份信息主要包括角色（如教师、学生等）和所属学院。这些信息存储在 MongoDB 的 user_profiles 集合中：

```py
# 创建用户身份信息（节选自 app.py）
profile_data = {
    "user_id": user_id,
    "role": "未设置",
    "college": "未设置",
    "age": None,
    "created_at": datetime.now(),
    "last_updated": datetime.now()
}
db.user_profiles.insert_one(profile_data)
```

##### 2. 个性化搜索实现

核心实现位于 SearchPersonalization 类中，主要包括以下关键功能：

##### 2.1 **学院关联关系定义**

为了实现**跨学院的内容推荐**，系统定义了学院间的关联关系：

```py
COLLEGE_RELATIONS = {
    '文学院': ['新闻与传播学院', '汉语言文化学院', '外国语学院'],
    '历史学院': ['文学院', '哲学院', '周恩来政府管理学院'],
    '物理科学学院': ['电子信息与光学工程学院', '材料科学与工程学院'],
    # ... 其他学院关系
}
```

##### 2.2 个性化权重计算

权重计算是个性化查询的核心，通过 _calculate_boost 方法实现(可扩展，部分展示）：

```py
def _calculate_boost(self, content, role, college, related_colleges):
    boost = 1.0
    
    # 基于角色的内容提升
    if role == '教师':
        if any(tag in content.lower() for tag in ['学术', '科研', '教学', '实验室', '课题']):
            boost *= 1.3
        if any(tag in content.lower() for tag in ['教务', '师资', '课程']):
            boost *= 1.2
    elif role in ['本科生', '研究生', '博士生']:
        if any(tag in content.lower() for tag in ['学生', '教务', '奖学金']):
            boost *= 1.2
        if any(tag in content.lower() for tag in ['就业', '实习', '竞赛', '社团']):
            boost *= 1.15
            
    # 学院相关性判断
    if college != '未设置':
        if college.lower() in content.lower():
            boost *= 1.4
        for related_college in related_colleges:
            if related_college.lower() in content.lower():
                boost *= 1.15
                
    return boost
```

##### 2.3 结果重排序

在搜索结果处理时，将原始搜索分数与个性化权重相结合：

```py
final_score = boost * (1 + 0.019 * base_score)
```

##### 2.4 PageRank 整合

系统将页面的 PageRank 值作为一个额外的权重因子：

```py
# 在搜索结果处理前，为每个结果获取 PageRank 值
for result in results:
    try:
        if hasattr(result, 'url'):
            url = result.url
            # 从数据库中查找对应 URL 的 pagerank 值
            page_data = db.NEWS.find_one({'url': url}, {'pagerank': 1})
            if page_data and 'pagerank' in page_data:
                setattr(result, 'pagerank', float(page_data['pagerank']))
            else:
                setattr(result, 'pagerank', 0)
    except Exception as e:
        print(f"获取 PageRank 值错误: {str(e)}")
        setattr(result, 'pagerank', 0)
```

PageRank 值通过对数函数进行平滑处理，避免权重差异过大：

```py
pr_boost = 1 + 0.05 * math.log1p(pagerank)
```

##### 3. 个性化指标

##### 3.1 角色维度：系统对不同角色用户实现了差异化的内容推荐：

- 教师用户：
  - 学术相关内容权重提升30%
  - 教务相关内容权重提升20%
- 学生用户：
  - 学生事务相关内容权重提升20%
  - 活动竞赛相关内容权重提升15%

##### 3.2 学院维度：基于学院的个性化包括三个层次：

1. 本院内容：权重提升40%
2. 关联学院内容：权重提升15%

```py
COLLEGE_RELATIONS = {
    '计算机学院': ['软件学院', '人工智能学院', '数学科学学院'],  # 兼容简称
    '网络空间安全学院': ['计算机学院', '软件学院', '数学科学学院'],  # 兼容分拆名称
    '数学科学学院': ['统计与数据科学学院', '计算机学院', '人工智能学院'],
    '经济学院': ['商学院', '金融学院', '统计与数据科学学院'],
    # ... 其他学院关系
}
```

3. 院系活动：

- 本院活动额外提升25%
- 关联学院活动额外提升10%

```py
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
#....其他院系相关关键词]
```

3.3 **PageRank：作为网页重要性的衡量指标，在个性化排序中起补充作用：**

1. 基础提升：高 PageRank 值的页面获得 5% * log(1 + PageRank) 的权重提升
2. 平滑处理：通过对数函数降低 PageRank 差异过大导致的排序偏差
3. 可靠性保证：当无法获取 PageRank 值时，系统会优雅降级到基于用户特征的排序

### 3.6 个性化推荐——搜索上的联想关联

不同账号下的**用户画像**、**搜索习惯**和**搜索内容**有区别

#### 示例结果：

计算机本科生xing，曾经搜索过夜跑活动（刚才的测试）：

![image-20241217231353742](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217231353742.png)

金融教师搜索（这里先删除了刚刚测试时的搜索记录）：

![image-20241217231856471](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217231856471.png)

#### 关键实现——代码简化

这里采用了三种策略

- 访问用户**搜索历史**，去查找是否有相关搜索记录，同时结合**标题长度惩罚**和**时间衰减**，历史记录中存在的搜索会赋予较高初始值，且根据**时间先后**赋予不同的分数；
- 同时根据**信息的匹配程度**赋予不同的分数（精确、前缀、包含三种匹配分）
- 根据**用户画像**（用户的身份和搜索偏好）提供除搜索历史相同的记录之外的联想推荐，并根据相关性设置排序，不同用户的推荐不同。

##### 1. 历史记录优先推荐

```py
# 从搜索历史获取建议
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
```

**历史记录匹配度评分**：

- 精确匹配：1000分——查询与历史记录完全相同，优先级最高
- 前缀匹配：800分——历史记录以查询内容开头，次优先级
- 包含匹配：600分——历史记录包含查询内容，基础优先级

```python
    regex_pattern = re.compile(f".*{re.escape(query)}.*", re.IGNORECASE)
    historical_queries = db.search_history.find({
        'user_id': user_id,
        'query': {'$regex': regex_pattern}
    }).sort('timestamp', -1)  # 按时间倒序排序

    suggestions = []
    for hist in historical_queries:
        text = hist['query'].lower()
        query_lower = query.lower()
        
        # 计算匹配度分数
        if text == query_lower:
            score = 1000  # 精确匹配
        elif text.startswith(query_lower):
            score = 800   # 前缀匹配
        else:
            score = 600   # 包含匹配
        
        # 时间衰减：7天内的记录获得额外分数
        days_old = (datetime.now() - hist['timestamp']).days
        if days_old <= 7:
            score += (7 - days_old) * 10

        suggestions.append({
            'text': hist['query'],
            'type': 'history',
            'score': score
        })
```

**时间衰减机制**：

- 7天时间窗口，仅对7天内的记录加分，每天递减10分，保证最近的搜索获得更高权重
- 衰减计算公式：extra_score = (7 - days_old) * 10

**标题长度优化**：

```python
 length_penalty = min(1.0, 50 / len(text)) if len(text) > 50 else 1.0
```

- 长度阈值：50字符，防止过长标题占据优势位置
- 惩罚公式：min(1.0, 50/title_length)
- final_score = base_score * length_penalty

##### 2. 个性化排序实现(集成pagerank)

```py
# 根据用户身份信息进行个性化权重调整
if user_profile:
    role = user_profile.get('role', '未设置')
    college = user_profile.get('college', '未设置')

    # 根据角色加权
    if role == '教师':
#具体关键词加权
    elif role in ['本科生', '研究生', '博士生']:
#具体关键词加权 
    # 根据学院加权
    if college != '未设置':
        if college.lower() in title.lower():
            suggestion['score'] *= 1.4
        # 获取相关学院
        related_colleges = SearchPersonalization.COLLEGE_RELATIONS.get(college, [])
        for related_college in related_colleges:
            if related_college.lower() in title.lower():
                suggestion['score'] *= 1.15
                break
    # PageRank加权
    if hasattr(result, 'url'):
        url = result.url
        # 从数据库中查找对应URL的pagerank值
        page_data = db.NEWS.find_one({'url': url}, {'pagerank': 1})
        if page_data and 'pagerank' in page_data:
            suggestion['score'] *= (1 + float(page_data['pagerank']))  # 将PageRank值作为权重因子
```

同时关注**历史记录**和搜索的相关性，添加时间衰减；同时参考**用户画像**影响排序策略。

### 3.7 Web界面设计

样式参见上方图片和视频演示，此处做补充和文字总结

#### 1. 整体架构设计

- 采用模块化设计思想，search.html主导航界面和preference.html(偏好设置表单）、history.html（搜索历史表单）、profile.html（身份信息表单）、snapshot.html（网页快照表单）各自独立相互配合
- 将不同功能的CSS文件分离（main.css, search.css, results.css等），提高了代码的可维护性和复用性
- 使用**MVC架构模式**，将视图(HTML模板)、控制器(JavaScript)和模型(数据处理)清晰分离
- 遵循**响应式设计**原则，确保在不同设备上都能提供良好的用户体验

#### 2. 核心功能模块

(1) **搜索界面**设计

- 提供多样化的搜索选项：基础搜索、文档搜索、短语搜索和通配符搜索
- 支持高级筛选功能：搜索范围选择（全部/标题/内容）、排序方式选择（相关度/时间）
- 针对文档搜索提供详细的文件类型筛选（PDF/DOC/DOCX/XLS/XLSX等）

(2) **搜索建议**实现

- 采用防抖（Debounce）技术优化实时搜索建议请求，提高性能
- 使用输入法组合事件处理，优化中文输入体验

(3) **搜索结果**展示

- 分类展示不同类型的搜索结果（普通网页/文档）
- 对于文档类搜索结果，展示详细元数据（文件类型、大小、上传时间等）
- 实现网页快照功能，保存历史版本
- 采用分页机制，支持自定义每页显示结果数

#### 3. **用户系统**设计

(1) 用户认证与管理

- 实现模态框形式的登录/注册界面，提升用户体验
- 支持用户头像显示（使用用户名首字母）
- 实现下拉菜单形式的用户功能导航

(2) 个性化功能

- 支持搜索历史记录的保存、展示和管理

- 提供个性化搜索偏好设置（**默认**搜索范围、排序方式、每页结果数）

![image-20241217234706993](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217234706993.png)

之后在搜索时就可以按照设置的偏好直接进行，同时更新MongoDB相应数据库偏好信息：

![image-20241217234622692](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241217234622692.png)

- 允许用户完善个人信息（身份、学院、年龄等）

#### 4. 技术亮点

(1) 性能优化

- 使用事件委托优化事件处理
- 实现搜索建议的智能防抖
- 采用异步加载技术（async/await）处理API请求

(2) 安全性考虑

- 实现跨站请求伪造（CSRF）防护
- 对用户输入进行转义处理，防止XSS攻击
- 实现安全的密码处理机制

## 四、项目总结

本项目实现了一个基于南开校内资源的搜索引擎ALLINKU。

#### 其实过程中还是遇到蛮多**困难**的...

文档爬取花费了不少时间，对于很多**知识的理解**开始有问题，导致代码大改了两次，不过多听了几遍最后一次实验课的录音，现在是满足需求的；

在实现新的功能的时候很容易和之前以后的功能在**前后端衔接**上出问题；

没有进行**版本控制**，导致有时候改了很多代码没进行测试，结果功能出问题的时候不知道从哪一步开始错的，只能凭借记忆Ctrl+Z，改不对就只能整个模块重新开始；

在开始没有规划好项目结构，没有在早期就实现代码功能**模块化**，同一个文件里面过长的代码和复杂交错的功能不利于项目推进，好在也及时按我的想法重构了一下，明显感觉进度快了不少，而且对应的问题也更方便找到相关的代码。

虽然遇到了不少困难，但是通过这个项目的开发，我也收获了不少，简单叙述一下：

1. 技术能力提升

- 深入理解了搜索引擎的核心原理，包括文档索引、链接分析和个性化推荐等
- 掌握了Whoosh、MongoDB等工具的实践应用
- 提升了Python全栈开发能力，特别是Flask框架的使用
- 学习了前端技术栈，提高了HTML、CSS和JavaScript的实战能力

2. 工程实践经验

- 完整经历了从需求分析、架构设计到具体实现的开发流程
- 学会了如何处理大规模数据和构建复杂系统
- 提高了代码组织、模块设计的能力
- 增强了性能优化和安全防护的意识

## 五、改进方向

1. 搜索算法优化

- 引入用户**点击反馈机制**，根据用户点击率**动态调整排序权重**
- 增加**用户停留时间分析**，将**浏览时长**作为内容质量的评判依据
- 实现**相关性反馈机制**，允许用户对搜索结果进行评分

2. 性能提升

- 实现分布式爬虫系统，提高**数据采集效率**
- **缓存热门搜索**结果，减轻数据库压力
- 优化数据库查询，优化**索引策略**

3. 功能扩展

- 增加语义理解能力，支持**同义词和近义词**查询
- 实现高级过滤器，支持更**复杂的组合查询**

4. 用户体验优化

- 引入搜索建议的机器学习模型，提供更**智能的联想**
- 增加个性化推荐的深度学习算法，提高**推荐准确度**
- 优化结果呈现方式，添加**结果预览**功能，提供更丰富的**数据可视化**展示

5. 未来项目！！！

- 提前做好项目规划，早期就对代码进行**模块化**，便于后期纠错和分模块优化
- 做好**版本控制**，出现问题方便及时回退
- 不要着急，做错了大不了重新开始，着急只会错上加错

===============================================================================

## Congratulations！

## 成功从0开始实现了搜索引擎的搭建！![19255F29](C:\Users\lenovo\AppData\Local\Temp\SGPicFaceTpBq\36344\19255F29.png)

完整项目：https://github.com/1Reminding/Information-Retrieval
