"""
# fetch测试chat接口
const data = {
    "params": {
        "promptList": [],
        "input": "\n          ***\n          名称：我是刑警;一句话推荐：;\n          ***\n          你是一名资深的运营编辑，需要完成节目运营相关工作，回答问题时抓取网络信息，结合以上剧名、描述以及网络抓取信息（***中间部分）回答，问题不相关字段不必返回，\n                回答问题时请先根据以下映射关系（包括处理动作，处理动作需要的参数，动作描述）（---之间部分）,首先识别出是否能用对应的动作处理，若能匹配对应动作，再识别出对应动作的参数要求，结果按照[{action: '',params: {}}]的json字符串格式输出，仅仅返回可通过JSON.parse处理的标准的json字符串格式即可，不要返回多余内容，params参数格式务必按照映射要求的格式返回；若不能匹配对应动作，直接回复问题答案即可。\n                ---\n                [{\"action\":\"updateCatalogInfo\",\"params\":{},\"description\":\"修改编目信息\"},{\"action\":\"deletePromotion\",\"params\":{\"orders\":[\"要删除的一句话推荐序号,多条逗号分割\"]},\"description\":\"删除一句话推荐\"},{\"action\":\"replacePromotion\",\"params\":{\"order\":\"要替换的序号，从1开始计数\",\"newPromotion\":\"新的一句话推荐\"},\"description\":\"替换一句话推荐\"}]\n                ---\n                现在请开始回答\n                生成编目信息\n                \n        ",
        "conversationTitle": "我是刑警",
        "channelName": "电视剧",
        "extraInfo":[],
        // "extraInfo": [{"type": 1, "value": "https://baike.baidu.com/item/%E6%88%91%E6%98%AF%E5%88%91%E8%AD%A6/54275286"}],
    }
};

const formData = new FormData();
formData.append("params", JSON.stringify(data.params));

fetch('/chat', {
    body: formData,
    method: 'POST',
})
.then((response) => {
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
})
.then((data) => {
    console.log('Received JSON response:', data);
})
.catch((error) => {
    console.error('Error:', error);
});
"""