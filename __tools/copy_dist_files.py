import os
import shutil

def main():
    # 目标文件夹路径
    target_dir = r"C:\Users\MI\Documents\HBuilderProjects\BlindMate"
    # dist文件夹路径
    dist_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

    # 检查目标文件夹是否存在
    if not os.path.exists(target_dir):
        print(f"目标文件夹 {target_dir} 不存在")
        return

    # 删除assets文件夹
    assets_path = os.path.join(target_dir, "assets")
    if os.path.exists(assets_path):
        try:
            shutil.rmtree(assets_path)
            print(f"已删除文件夹: {assets_path}")
        except Exception as e:
            print(f"删除assets文件夹失败: {e}")

    # 删除index.html
    index_path = os.path.join(target_dir, "index.html")
    if os.path.exists(index_path):
        try:
            os.remove(index_path)
            print(f"已删除文件: {index_path}")
        except Exception as e:
            print(f"删除index.html失败: {e}")

    # 检查dist文件夹是否存在
    if not os.path.exists(dist_dir):
        print(f"dist文件夹 {dist_dir} 不存在")
        return

    # 复制dist文件夹内容到目标文件夹
    try:
        for item in os.listdir(dist_dir):
            src = os.path.join(dist_dir, item)
            dst = os.path.join(target_dir, item)
            
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            
            print(f"已复制: {src} -> {dst}")
        
        print("文件复制完成")
    except Exception as e:
        print(f"复制文件时出错: {e}")

if __name__ == "__main__":
    main()