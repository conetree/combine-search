def render_page(data):
    html_template = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>AI网页抓取方式</title>
            <style>
                /* Your CSS styles here */
                .search-container {{
                    text-align: center;
                    margin-bottom: 20px;
                }}
                .search-input {{
                    width: 40%;
                    padding: 10px;
                    font-size: 16px;
                    height: 16px;
                    padding: 12px 16px;
                    margin: 0;
                    vertical-align: top;
                    outline: 0;
                    box-shadow: none;
                    border-radius: 10px 0 0 10px;
                    border: 2px solid #06b6b1;
                    background: #fff;
                    color: #222;
                    overflow: hidden;
                    box-sizing: content-box;
                }}
                .search-button {{
                    font-size: 16px;
                    cursor: pointer;
                    width: 108px;
                    height: 44px;
                    line-height: 45px;
                    line-height: 44px \9;
                    padding: 0;
                    background: 0 0;
                    background-color: #06b6b1;
                    border-radius: 0 10px 10px 0;
                    font-size: 17px;
                    color: #fff;
                    box-shadow: none;
                    font-weight: 400;
                    border: none;
                    outline: 0;
                }}
                .options-container {{
                    text-align: left;
                    margin-top: 1em;
                    margin-right: 6em;
                    text-align: center;
                    font-size: 14px;
                }}
                .results-container {{
                    margin: 10px;
                    white-space: pre-wrap;
                    background-color: #ecf7f7;
                    /* border: 1px solid #06b6b1; */
                    padding: 10px;
                    border-radius: 10px;
                }}
                .search-method-table {{
                    border: 1px solid #eee; 
                    border-collapse: collapse; 
                    margin: auto 10px;
                    border-spacing: 5px;
                    width: 100%;
                    border-collapse: separate;
                    border-spacing: 0;
                    border-radius: 10px;
                    overflow: hidden;
                    border: 1px solid #ddd;
                }}
                .search-method-table th, td {{
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                }}
                .search-method-table tr:last-child td {{
                    border-bottom: none;
                }}
                .search-links {{
                    margin: 0 auto;
                    margin-bottom: 5px;
                    padding-right: 5em;
                    width: 50%;
                    # text-align: left;
                }}
                .search-link {{
                    margin: 0 5px;
                    cursor: pointer;
                    color: #06b6b1;
                    text-decoration: underline;
                    font-size: 1.2em;
                }}
                .search-link.selected {{
                    font-weight: bold;
                    text-decoration: none;
                    color: #000;
                }}
            </style>
        </head>
        <body>
            <div class="search-container">
                <h1>基于剧名抓取网络数据</h1>
                <form id="search-form" action="/search/duckduckgo-web">
                    <div class="search-links">
                        <span class="search-link" data-url="/search/bing-web" title="bing搜索">Bing</span>
                        <span class="search-link" data-url="/search/baidu-web" title="百度搜索">百度</span>
                        <span class="search-link" data-url="/search/duckduckgo-web" title="Duckduckgo搜索">DuckDuckGo</span>
                        <span class="search-link" data-url="/search/google-web" title="Google搜索">Google</span>
                        <span class="search-link" data-url="/search/sogou-web" title="搜狗搜索">搜狗</span>
                        <span class="search-link" data-url="/search/so-web" title="360搜索">360</span>
                        <span class="search-link" data-url="/search/douban-web" title="豆瓣电影">豆瓣</span>
                    </div>
                    <input type="text" id="search-query" name="q" class="search-input" value="我是刑警 电视剧 豆瓣 百科" placeholder="请输入关键词：狂飙 电视剧 百科 豆瓣"><button type="submit" class="search-button">搜索</button>
                    <div class="options-container">
                        工具：
                        <label><input type="radio" name="http_tool" value="request" checked> request</label>
                        <label><input type="radio" name="http_tool" value="curl"> curl</label>
                        <label><input type="radio" name="http_tool" value="agent"> agent</label>
                        <label><input type="radio" name="http_tool" value="firecrawl"> firecrawl</label>
                        <label><input type="radio" name="http_tool" value="selenium"> selenium</label>
                        <label><input type="radio" name="http_tool" value="scrapy"> scrapy</label>
                        <label><input type="radio" name="http_tool" value="cloudscraper"> cloudscraper</label>
                        <label><input type="radio" name="http_tool" value="playwright"> playwright</label>
                    </div>
                    <div class="options-container">
                        返回：
                        <label><input type="radio" name="mode" value="text" checked> 文本模式</label>
                        <label><input type="radio" name="mode" value="html"> HTML模式</label>
                        <label><input type="radio" name="mode" value="link"> 链接模式</label>
                    </div>
                </form>
            </div>

            <div class="results-container"><code id="search-results">这是根据节目名称和频道等关键词从搜索引擎获取结果，再抓取豆瓣和百科词条的工具。有多种搜索引擎和抓取工具组合，提高抓取成功率。支持mode,http_tool,links_num参数。</code></div>

            <div style="display: flex; justify-content: center;">
                <!--<h1>{message}</h1>-->
                <table class="search-method-table">
                    {paths_list}
                </table>
            </div>
            <script>
                const $searchForm = document.getElementById('search-form');
                const $query = $searchForm.querySelector('#search-query');
                const defaultQuery = $query.value;
                const $result = document.getElementById('search-results');
                const $searchLinks = document.querySelectorAll('.search-link');

                const baiduSearchValue = '我是刑警 site:movie.douban.com';

                function selectLink(link) {{
                    $searchLinks.forEach(l => l.classList.remove('selected'));
                    link.classList.add('selected');
                    const doubanUrl = '/search/douban-web'
                    const baiduUrl = '/search/baidu-web'
                    if(link.getAttribute("data-url") == doubanUrl) {{
                        $query.value = defaultQuery.substr(0, defaultQuery.indexOf(" "));
                    }} else if(link.getAttribute("data-url") == baiduUrl) {{
                        $query.value = baiduSearchValue;
                    }} else {{
                        $query.value = defaultQuery;
                    }}
                    $searchForm.setAttribute('action', link.getAttribute('data-url'));
                }}

                $searchLinks.forEach(link => {{
                    link.addEventListener('click', () => {{
                        selectLink(link);
                    }});
                }});

                if ($searchLinks.length > 0) {{
                    selectLink($searchLinks[0]);
                }}

                async function handleSubmit(event) {{
                    event.preventDefault();
                    $result.innerHTML = "<strong>正在搜索中，请稍等...</strong>";
                    const query = $query.value;
                    const mode = $searchForm.querySelector('input[name="mode"]:checked').value;
                    const http_tool = $searchForm.querySelector('input[name="http_tool"]:checked').value;
                    const url = $searchForm.action + `?q=${{encodeURIComponent(query)}}&mode=${{mode}}&http_tool=${{http_tool}}`
                    const response = await fetch(url);
                    const result = await response.text();
                    $result.textContent = JSON.stringify(JSON.parse(result), null, 2);
                }}

                document.addEventListener('DOMContentLoaded', () => {{
                    $searchForm.addEventListener('submit', handleSubmit);
                }});
            </script>
        </body>
        </html>
        """

    paths_list = ""
    for index, path_info in enumerate(data["paths"]):
        bg_color = "#eee;" if index % 2 == 1 else "white"
        paths_list += f"""
        <tr style="background-color: {bg_color}; border: 1px solid #06b6b1;">
            <td style="padding: 5px;">
                <a href="{path_info['path']}">{path_info['path']}</a>
            </td>
            <td>{path_info['desc']}</td>
        </tr>
        """

    html_content = html_template.format(
        message=data["message"], paths_list=paths_list)
    return html_content
