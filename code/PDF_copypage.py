import os
from PyPDF2 import PdfReader, PdfWriter

def copy_page_to_end(input_path, output_folder, page_number, copy_times=1):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 如果是单个文件，直接放入列表处理
    if os.path.isfile(input_path):
        pdf_files = [input_path]
    else:
        pdf_files = [
            os.path.join(input_path, f) for f in os.listdir(input_path) if f.endswith(".pdf")
        ]

    for input_file in pdf_files:
        filename = os.path.basename(input_file)
        try:
            output_path = os.path.join(output_folder, filename)

            reader = PdfReader(input_file)
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            if 1 <= page_number <= len(reader.pages):
                page_to_copy = reader.pages[page_number - 1]

                for _ in range(copy_times):
                    writer.add_page(page_to_copy)

                with open(output_path, 'wb') as f_out:
                    writer.write(f_out)
                print(f"{filename}: 成功")
            else:
                print(f"{filename}: 失败（页码超出范围）")

        except Exception as e:
            print(f"{filename}: 失败（{type(e).__name__}）")

# 示例使用
input_path = R"C:\Desktop\PDF图片测试.pdf"  # 你可以给单个PDF文件
output_folder = R"C:\Desktop" # 输出文件夹
page_number = 2      # 复制第2页
copy_times = 9950    # 复制10000次

copy_page_to_end(input_path, output_folder, page_number, copy_times)
