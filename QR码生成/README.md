### 二维码生成器（可控参数版）

本项目提供一个桌面 GUI 应用，可自定义下列二维码参数：
- 版本（1-40，或自动）
- 纠错等级（L/M/Q/H）
- 像素大小 `box_size`
- 边框 `border`
- 前景/背景颜色
- 输出格式：PNG 或 SVG
- Logo 嵌入（仅 PNG 支持），占二维码宽度 5%~40%

### 运行环境
- Python 3.9+（建议 3.10/3.11/3.12）
- Windows、macOS、Linux 均可运行

### 安装依赖
```bash
pip install -r requirements.txt
```

若国内网络安装缓慢，可使用镜像：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 启动
```bash
python main.py
```

### 使用说明
1. 在左侧输入框输入文本/URL/JSON 等内容，或通过“从文件载入…/粘贴剪贴板”导入。
2. 右侧设置参数：版本、纠错等级、像素、边框、前景/背景色、输出格式。
3. 若需嵌入 Logo（仅 PNG）：选择图片并设置占比（5%~40%）。
4. 点击“生成预览”查看效果；点击“保存…”导出 PNG/SVG 文件。

### 注意事项
- 选择 SVG 输出时不支持嵌入位图 Logo。
- 若选择固定版本且内容超出容量，请提高版本或纠错等级，或启用“自动”。
- 颜色使用十六进制色值（如 `#000000`）。

### 许可证
MIT
