"""
用来定义agent的主要的代码,
"""
from langchain.tools import tool
import pymysql
import os
from dotenv import load_dotenv
from pathlib import Path
from pymysql.cursors import DictCursor
from sqlalchemy import text
load_dotenv()
root_path = Path(__file__).parent.parent
embeddings =None
milvus_client = None
engine = None
agent = None
def get_embeddings():
    global embeddings
    if embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model=str(root_path / "models" / "bge-m3"))
    return embeddings

def get_milvus_client():
    global milvus_client
    if milvus_client is None:
        from pymilvus import MilvusClient
        milvus_client = MilvusClient(
            uri=os.getenv("MILVUS_URI"),
            token=os.getenv("MILVUS_TOKEN")
        )
    return milvus_client

def mysql_connection():
    global engine
    if engine is None:
        from sqlalchemy import create_engine
        from urllib.parse import quote_plus
        # 注释：密码里的 @ : / 等特殊字符必须做 URL 编码，
        # 否则 SQLAlchemy 会把密码里的 @ 当成用户名与主机名的分隔符
        engine = create_engine(
            url=f"mysql+pymysql://{quote_plus(os.getenv('MYSQL_USERNAME'))}:{quote_plus(os.getenv('MYSQL_PASSWORD'))}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}",
            pool_size=15
        )
    return engine


@tool
def search_main_dishes():
    """
    用来搜索餐厅当中的主菜
    """
    key_name_mapping={
        "dish_name":"主菜名称",
        "price":"价格",
        "description":"描述",
        "category":"分类",
        "spice_level":" 辣度等级",
        "flavor":"口味",
        "main_ingredients":"主要食材",
        "cooking_method":"烹饪方法",
        "is_vegetarian":"是否为素食",
        "allergens":"过敏信息"
    }
    with pymysql.connect(host=os.getenv("MYSQL_HOST"),
                         user=os.getenv("MYSQL_USERNAME"),
                         password=os.getenv("MYSQL_PASSWORD"),port=int(os.getenv("MYSQL_PORT"))) as conn:
        with conn.cursor(DictCursor) as cursor:
            sql = """
                select
                    dish_name,
                    price,
                    description,
                    category,
                    spice_level,
                    flavor,
                    main_ingredients,
                    cooking_method,
                    is_vegetarian,
                    allergens
                from
                    menu.menu_items
                where
                    is_featured=1
            """

            cursor.execute(sql)
            results = cursor.fetchall()
            # 定义json的键，将数据封装成json
            json_results = []
            for item in results:
                json_item = {}
                for key, value in item.items():
                    json_item[key_name_mapping[key]] = value
                json_results.append(json_item)
            
            return json_results
            
            # 定义json的键，将数据封装成json



@tool
def user_flavor_search(user_query:str):
    """
    基于用户的口味，来去查找相关的菜品
    """
    import pymilvus
    from langchain_huggingface import HuggingFaceEmbeddings

    # 1、构建用户query的向量
    embeddings = get_embeddings()

    query_vector = embeddings.embed_query(user_query)

    # 2、连接milvus，进行向量搜索
    client = get_milvus_client()

    # 3、进行向量搜索
    search_res = client.search(
        collection_name="menu_items",
        data=[query_vector],
        anns_field="vector",
        output_fields=["text"],
        limit=1
    )
    print("当前查找结果为：",search_res)
    # 4、解析搜索结果
    if search_res:
        all_results = search_res[0]
        # all_results: 列表
        final_result = []

        for item in all_results:
            item_str = item["entity"]['text']
            final_result.append(item_str)
        
        return final_result
    else:
        return "在当前库里面没有找到和用户喜好相关的菜品"
    
from pydantic import BaseModel,Field

class ReservationToolArgsInfo(BaseModel):
    num_people:int = Field(description="预约的总人数")
    num_children:int = Field(description="预约的0-2岁儿童人数")
    arrival_time:str = Field(description="预约的到达时间,格式：YYYY-MM-DD HH")
    seat_preference:str = Field(description="预约的座位偏好，当用户没有特殊需求时，传递空字符串即可")
    main_dish_preference:str = Field(description="预约的主菜偏好，当用户没有特殊需求时，传递空字符串即可")
    comment:str = Field(description="预约的其他备注，当用户没有特殊需求时，传递空字符串即可")

@tool(args_schema=ReservationToolArgsInfo)
def make_reservation(num_people:int,num_children:int,arrival_time:str,seat_preference:str,main_dish_preference:str,comment:str):
    """
    用来进行餐厅预定的工具：
    通过MySQL向数据库当中写入数据
    """
    engine = mysql_connection()
    with engine.connect() as conn:
        sql = """
INSERT INTO reservation_order
(num_people, num_children, arrival_time, seat_preference, main_dish_preference, other_comments)
VALUES
(:num_people, :num_children, :arrival_time, :seat_preference, :main_dish_preference, :other_comments)
"""
        # 
        params = {
    "num_people": num_people,
    "num_children": num_children,
    "arrival_time": arrival_time,
    "seat_preference": seat_preference,
    "main_dish_preference": main_dish_preference,
    "other_comments": comment,
}
        conn.execute(statement=text(sql),parameters=params)

        conn.commit()

        return "预订成功"
    
async def assistant_query(user_query:str):
    """
    接收来自前端的用户query,使用agent进行回复
    """
    agent = await create_agent()
    # 1、调用前，新添加一个system prompt，让agent感知当前的时间
    from datetime import datetime
    from langchain.messages import ToolMessage
    current_date = datetime.now().strftime("%Y-%m-%d")
    day_of_week = datetime.now().weekday() + 1
    time_system_prompt = {"role":"system","content":f"当前日期为：{current_date}，当前是周{day_of_week}"}

    # 2、config如何去构建：在实际的生产环境下，每个用户的每一次会话，在后端系统当中，都会有一个session_id，可以拿这个session_id作为thread_id传进去
    config = {"configurable":{"thread_id":123}}
    # res = await agent.ainvoke({"messages":[time_system_prompt,{"role":"user","content":user_query}]},config=config)

    # 3、如何去调用agent: 通过流式输出
    async for chunk in agent.astream({"messages":[time_system_prompt,{"role":"user","content":user_query}]},config=config,stream_mode="messages"):
        # chunk首先一个tuple:(AIMessageChunk/ToolMessage,_)
        message = chunk[0]
        if type(message) == ToolMessage:
            continue
        # 这个message 需要通过什么方式，给到谁：需要通过接口的方式，给到前端，然后让前端去展示？
        # SSE: Server-Sent Events 
        # SSE的数据结构：data: {"type":"token","content":"你好"}\n\n

        # 快速地将这个方法产出的token，给到后端接口，让后端接口去输出给前端
        import json
        payload = {"content":message.content,"type":"token"}
        payload_str = json.dumps(payload,ensure_ascii=False)
        yield f'data: {payload_str}\n\n'


    



async def create_agent():
    global agent 
    if agent is None:
        from pathlib import Path
        from langchain.agents import create_agent
        from langchain_openai import ChatOpenAI
        from langchain_mcp_adapters.client import MultiServerMCPClient
        from langgraph.checkpoint.memory import InMemorySaver


        checkpointer = InMemorySaver()

        client  = MultiServerMCPClient(
            connections={
                "amap_map":{
            "transport": "sse",
            "url": "https://mcp.api-inference.modelscope.net/ccaef2a2308042/sse"
            }

            }
        )
        
        # 注释：model / base_url 改为从 .env 读取，
        # 官方 api.openai.com 在国内直连不通，必须走中转或换国内兼容接口
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
        with open(str(root_path / 'agent' /"prompts" / 'system_prompt.txt'),encoding="utf-8",mode="r") as f:
            system_prompt = f.read()
        mcp_tools = await client.get_tools()
        agent = create_agent(
            model=llm,
            system_prompt=system_prompt,
            tools=[search_main_dishes,user_flavor_search,make_reservation]+mcp_tools,
            checkpointer=checkpointer
        )
    return agent

async def test_agent():
    agent = await create_agent()
    config = {"configurable":{"thread_id":"123"}}
    res = await agent.ainvoke({"messages":[{"role":"user","content":"你能为我做什么？"}]},config=config)

    print(res["messages"][-1].content)

if __name__ == '__main__':
    import asyncio
    asyncio.run(test_agent())
    