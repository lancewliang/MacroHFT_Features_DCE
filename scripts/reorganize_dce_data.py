#!/usr/bin/env python3
"""
重新组织豆珀数据文件
将 豆珀2023-2025 目录中的zip文件解压并重新组织为：品种/年份/月份/ 的结构
"""

import os
import zipfile
import shutil
from pathlib import Path


def reorganize_dce_data():
    # 源目录和目标目录
    source_dir = Path("./data/豆珀2023-2025")
    target_base_dir = Path("./data/豆珀_重组")

    # 品种名称（豆粕的拼音缩写是m）
    variety_name = "豆粕"

    # 创建目标基础目录
    target_base_dir.mkdir(parents=True, exist_ok=True)

    # 获取所有zip文件
    zip_files = sorted(source_dir.glob("*.zip"))

    print(f"找到 {len(zip_files)} 个zip文件")

    for zip_file in zip_files:
        # 从文件名提取年份和月份 (例如: 202301.zip -> 2023, 01)
        filename = zip_file.stem  # 去掉.zip后缀
        if len(filename) != 6 or not filename.isdigit():
            print(f"跳过格式不正确的文件: {zip_file.name}")
            continue

        year = filename[:4]
        month = filename[4:6]

        # 创建目标目录: 品种/年份/月份
        target_dir = target_base_dir / variety_name / year / month
        target_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n处理 {zip_file.name} -> {variety_name}/{year}/{month}/")

        # 解压文件
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                # 获取压缩包中的所有文件
                file_list = zip_ref.namelist()
                print(f"  解压 {len(file_list)} 个文件...")

                # 解压到目标目录
                zip_ref.extractall(target_dir)

            print(f"  ✓ 完成解压到 {target_dir}")

        except Exception as e:
            print(f"  ✗ 解压失败: {e}")
            continue

    print(f"\n所有文件已重新组织到: {target_base_dir}")

    # 显示目录结构概览
    print("\n目录结构预览:")
    for variety_dir in sorted(target_base_dir.glob("*")):
        if variety_dir.is_dir():
            print(f"\n{variety_dir.name}/")
            for year_dir in sorted(variety_dir.glob("*")):
                if year_dir.is_dir():
                    print(f"  {year_dir.name}/")
                    for month_dir in sorted(year_dir.glob("*")):
                        if month_dir.is_dir():
                            file_count = sum(1 for _ in month_dir.rglob("*") if _.is_file())
                            print(f"    {month_dir.name}/ ({file_count} 个文件)")


if __name__ == "__main__":
    reorganize_dce_data()
