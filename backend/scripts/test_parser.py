import os
import sys
from pathlib import Path

# 添加 backend 目录到 sys.path，以便导入 app 模块
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.core.file_parser import parse_file_content

def test_parser(file_path_str):
    path = Path(file_path_str)
    if not path.exists():
        print(f"❌ 文件不存在: {path}")
        return

    print(f"\n{'='*20} 测试文件: {path.name} {'='*20}")
    print(f"绝对路径: {path.resolve()}")
    
    try:
        with open(path, 'rb') as f:
            file_bytes = f.read()
        
        print(f"文件大小: {len(file_bytes)} bytes")
        
        # 调用解析核心
        result = parse_file_content(file_bytes, path.name)
        
        print(f"\n--- 解析结果预览 (前 1000 字符) ---")
        print(result[:1000])
        print(f"\n--- 解析结果长度: {len(result)} ---")
        
        if len(result) < 50:
            print("⚠️ 警告: 解析内容过短，可能解析失败或为空")
        else:
            print("✅ 解析看起来有内容")
            
    except Exception as e:
        print(f"❌ 解析过程抛出异常: {e}")

if __name__ == "__main__":
    # 自动查找 uploads 目录下的最新几个文件进行测试
    uploads_dir = backend_dir / "uploads"
    if not uploads_dir.exists():
        print(f"Uploads 目录不存在: {uploads_dir}")
        sys.exit(1)
        
    print(f"正在扫描 {uploads_dir} ...")
    
    # 获取所有文件
    files = sorted(uploads_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not files:
        print("Uploads 目录下没有文件")
    else:
        # 取最近的 5 个文件测试
        for f in files[:5]:
            if f.is_file():
                test_parser(str(f))

