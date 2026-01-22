import webview
import sys
import ctypes

# 服务器地址
# 注意：务必带上端口号，如果您的服务在 80 端口则不需要
SERVER_URL = "http://42.121.216.117"

def on_loaded():
    print("应用已加载")

if __name__ == '__main__':
    # 尝试设置 DPI 感知，防止在高分屏下模糊
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # 创建窗口
    window = webview.create_window(
        title='智能订单助手',
        url=SERVER_URL,
        width=1440,
        height=900,
        min_size=(1024, 768),
        resizable=True,
        # text_select=True, # 允许选择文本
        confirm_close=True, # 关闭时提示确认
    )
    
    # 启动
    # private_mode=False: 禁用隐身模式，允许保存 Cookie/LocalStorage
    # ssl=False: 允许不安全的 HTTP 内容（虽然主要取决于服务器配置）
    webview.start(func=on_loaded, gui='edgechromium', debug=False, private_mode=False)
