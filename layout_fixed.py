import json


def fix_canvas_layout(file_path, output_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. 获取 Graph 数据
    graph = data.get('omProcessGraph', {})
    nodes_str = graph.get('processNodes', '[]')
    edges_str = graph.get('processEdges', '[]')

    nodes = json.loads(nodes_str) if isinstance(nodes_str, str) else nodes_str

    print(f"原始模块数量: {len(nodes)}")

    # 2. 坐标重排 (Layout Normalization)
    # 简单的网格布局策略: 每行放 5 个，间距 300x200
    grid_cols = 5
    x_spacing = 300
    y_spacing = 200
    start_x = 100
    start_y = 100

    for i, node in enumerate(nodes):
        row = i // grid_cols
        col = i % grid_cols

        new_x = start_x + (col * x_spacing)
        new_y = start_y + (row * y_spacing)

        # 更新坐标
        node['x'] = new_x
        node['y'] = new_y

        # 可选: 重置所有 Status 状态，让前端重新计算
        if 'data' in node:
            node['data']['status'] = ""

    print("✅ 坐标已重置到可视区域 (100~2000 像素范围)")

    # 3. 回写数据
    if isinstance(nodes_str, str):
        graph['processNodes'] = json.dumps(nodes)  # 保持字符串格式
    else:
        graph['processNodes'] = nodes

    # 4. 强制同步 Project/Graph ID (防止链接断开)
    # 使用一个新的 ID 确保不缓存
    new_process_id = "process_fixed_layout_001"
    data['omProcessArchive']['processId'] = new_process_id
    data['omProcessGraph']['id'] = new_process_id

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"🎉 文件已修复并保存为: {output_path}")

# 请在你的本地环境中运行:
# fix_canvas_layout('final_result.json', 'final_fixed_layout.json')