import pikepdf
import time
import sys
import pyfiglet
from colorama import init, Fore
from rich.progress import Progress

# 渐变类型与中文名称的映射
shading_type_map = {
    1: "线性渐变 (Axial)",
    2: "径向渐变 (Radial)",
    3: "自由渐变 (Gouraud)",
    4: "网格渐变 (Mesh)",
    5: "PostScript 渐变 (过时)"
}


# 列出单页中XObject图像和Shading图像
def list_xobjects_and_shadings(page):
    result = {
        'images': [],  # 每个元素是 (name, width, height)
        'shadings': [],  # 每个元素是 (name, shading_type, coords)
        'watermarks': []  # 每个元素是 (name, resources, bbox)
    }
    try:
        resources = page.obj.get('/Resources')
        shadings = resources.get('/Shading')
        xobjects = resources.get('/XObject')

        # 处理XObject图像
        if xobjects is None: return result
        for name, obj_ref in xobjects.items():
            try:
                # 安全解引用
                try:
                    obj = obj_ref.get_object()
                except AttributeError:
                    obj = obj_ref
                subtype = obj.get('/Subtype')

                if subtype == '/Image':
                    width = obj.get('/Width', 'Unknown')
                    height = obj.get('/Height', 'Unknown')
                    result['images'].append((name, width, height))

                elif subtype == '/Form':  # 检查是否为水印 (Form)
                    # 提取水印的资源和边界框
                    resources = obj.get('/Resources', 'Unknown')
                    bbox = obj.get('/BBox', 'Unknown')
                    bbox_list = [float(coord) for coord in bbox] if bbox else None
                    result['watermarks'].append((name, resources, bbox_list))

            except Exception as e_inner:
                print(f"⚠️ 哎呀! 无法读取 {name} 对象: {type(e_inner).__name__}: {e_inner}")
                continue
        # 处理Shading图像
        if shadings is None: return result
        for name, obj_ref in shadings.items():
            try:
                # 安全解引用
                try:
                    obj = obj_ref.get_object()
                except AttributeError:
                    obj = obj_ref
                shading_type = obj.get('/ShadingType', 'Unknown')
                coords = obj.get('/Coords', None)
                coords_list = [float(coord) for coord in coords] if coords else None
                result['shadings'].append((name, shading_type, coords_list))

            except Exception as e_inner:
                print(f"⚠️ 哎呀! 无法读取 Shading {name}: {type(e_inner).__name__}: {e_inner}")
                continue
    except Exception as e:
        print(f"⚠️ 糟糕! 列出XObject时出错: {type(e).__name__}: {e}")
    return result


# 打印单页中XObject图像、Shading图像和水印图像
def print_xobjects_and_shadings(page):
    resources_info = list_xobjects_and_shadings(page)
    images = resources_info['images']
    shadings = resources_info['shadings']
    watermarks = resources_info['watermarks']
    print("🖼️ 文档一般图片：")
    if images:
        for name, width, height in images:
            print(f"  - 名字: {name}, 宽度: {width}, 高度: {height}")
    else:
        print("  - 无")
    print("🎨 渐变背景图片：")
    if shadings:
        for name, shading_type, coords_list in shadings:
            print(
                f"  - 名字: {name}, 类型: {shading_type}-{shading_type_map.get(shading_type, '未知')}, 坐标: {coords_list}")
    else:
        print("  - 无")
    print("💧 水印图片：")
    if watermarks:
        for name, resources, bbox in watermarks:
            resource_type = "图片" if "/Image" in str(resources) else "文字"
            print(f"  - 名字: {name}, 类型: {resource_type}, 边界: {bbox}")
    else:
        print("  - 无")
    return resources_info


# 删除指定的XObject或Shading对象
def remove_targets_from_page(page, targets, resources_info):
    deleted_count = 0
    try:
        resources = page.obj.get('/Resources')
        xobjects = resources.get('/XObject')
        shadings = resources.get('/Shading')
        # 删除所有XObject图像
        if '-a' in targets:
            try:
                if xobjects is not None:
                    # for name in list(xobjects.keys()):
                    #     del xobjects[name]
                    #     deleted_count += 1
                    # 删除 XObject 中列出的图片
                    for name, _, _ in resources_info.get('images', []):
                        if name in xobjects:
                            del xobjects[name]
                            deleted_count += 1
                    # 删除 watermarks 中列出的水印
                    for name, _, _ in resources_info.get('watermarks', []):
                        if name in xobjects:
                            del xobjects[name]
                            deleted_count += 1
                # 删除所有Shading对象
                if shadings is not None:
                    for name in list(shadings.keys()):
                        del shadings[name]
                        deleted_count += 1
            except Exception as e_inner:
                print(f"⚠️ 删除 {name} 失败: {type(e_inner).__name__}: {e_inner}")
        elif targets:
            # targets = [f'/{target}' for target in targets]
            # targets = {target: True for target in targets}
            for name in targets:
                try:
                    # 尝试从 XObject 中删除
                    if xobjects is not None and name in xobjects:
                        del xobjects[name]
                        deleted_count += 1
                    # 尝试从 Shading 中删除
                    elif shadings is not None and name in shadings:
                        del shadings[name]
                        deleted_count += 1
                except Exception as e_inner:
                    print(f"⚠️ 删除 {name} 失败(没有这个对象哦！): {type(e_inner).__name__}: {e_inner}")
                    continue
    except Exception as e:
        print(f"⚠️ 读取页面资源时出错: {type(e).__name__}: {e}")
    return deleted_count


# 解密PDF文件，没密码自动跳过
def decrypt_pdf(input_pdf_path):
    try:
        pdf = pikepdf.open(input_pdf_path)
        # 获取页码数
        page_count = len(pdf.pages)  # 获取页数
        # 判断是否加密
        if not pdf.is_encrypted:
            pdf.close()
            return input_pdf_path, page_count
        pdf.close()
        # 如果加密，重新用密码打开
        pdf = pikepdf.open(input_pdf_path)
        output_file = input_pdf_path.replace('.pdf', '(decrypted).pdf')
        pdf.save(output_file)
        pdf.close()
        print(f"\033[31m✅ 解密成功，保存为 {output_file}\033[0m")
        return output_file, page_count

    except pikepdf.PasswordError:
        print("❌ 无法解密(可能加密太高级了吧~)")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 啊哦！你这可不是PDF文件哦(有可能路径错了🤔): {e}\n\n")
        return "", 0


# 处理PDF文件，遍历每一页
def process_pdf(input_path, output_path, targets, resources_info):
    pdf = pikepdf.open(input_path)
    total_deleted_count = 0
    Indirect_page_count = 0
    total_pages = len(pdf.pages)
    start_time = time.time()

    with Progress() as progress:
        task = progress.add_task(f"⏳ 共{total_pages}页处理进度:", total=total_pages)
        for page_num, page in enumerate(pdf.pages):
            try:
                deleted_count = remove_targets_from_page(page, targets, resources_info)
                total_deleted_count += deleted_count
                if deleted_count == 0:
                    Indirect_page_count += 1
            except Exception as e:
                print(f"第 {page_num + 1} 页处理失败: {type(e).__name__}: {e}")
            progress.update(task, advance=1)

    elapsed_time = time.time() - start_time
    pdf.save(output_path)
    pdf.close()

    print(f"\n✨ 好耶！新文件已保存为: {output_path}")
    print(f"🥳 共删除 {total_deleted_count} 个对象!(有{Indirect_page_count}页为跨页共享~)")
    print(f"⏱️ 总耗时: {elapsed_time:.3f} 秒\n\n")
    print("🤠 来，继续！")


# 主函数
def main():
    while True:
        try:
            # 输入PDF文件的路径
            while True:
                input_file = input("📚️ 请输入PDF文件的路径: ")
                if input_file:
                    input_file = input_file.strip('"').strip("'")
                    input_file, page_count = decrypt_pdf(input_file)  # 尝试解密PDF文件
                    if page_count: break

            # 打开PDF并显示所有图像元素（XObject、Shading和水印）
            with pikepdf.open(input_file) as pdf:
                print("\033[34m🚀 PDF已加载，默认显示第 1 页(模板页)的所有图像:\033[0m")
                resources_info = print_xobjects_and_shadings(pdf.pages[0])

            # 选择模板
            page_num_input = input(f"\n\033[32m🎉 想换个模板页吗？输入页数（2 ~ {page_count} 之间），或者直接回车哦: \033[0m")
            if page_num_input:
                try:
                    page_num = int(page_num_input)
                    if 2 <= page_num <= page_count:
                        with pikepdf.open(input_file) as pdf:
                            print(f"\033[34m🚀 PDF再加载，显示第 {page_num} 页(模板页)的所有图像:\033[0m\n")
                            resources_info = print_xobjects_and_shadings(pdf.pages[page_num-1])
                    elif page_num != 1:
                        print(f"\033[32m😬 啥？啥？啥？你输入的是个啥？我直接一个忽略!\033[0m")
                except ValueError:
                    print(f"\033[32m😬 啥？啥？啥？你输入的是个啥？我直接一个忽略!\033[0m")

            # 提示用户输入要删除的目标对象
            targets_input = input("\n\033[35m🧰 请输入要删除的目标对象（如IM23, SD8, Form1), 用逗号分隔, 或者回车删除全部：\033[0m\n ")
            output_file = input_file.replace('.pdf', '_removed_images.pdf')
            if targets_input == "":
                targets = ["-a"]
                process_pdf(input_file, output_file, targets, resources_info)
            else:
                found = False
                targets = [target.strip() for target in targets_input.split(",")]
                targets = [f'/{target}' for target in targets]
                for target in targets:
                    if found: break
                    for category, items in resources_info.items():
                        if found: break
                        for item in items:
                            if target == item[0]:
                                found = True
                                break
                if found:
                    process_pdf(input_file, output_file, targets, resources_info)
                else:
                    print("\033[33m🫠  就不想删除呗，我再来！\033[0m\n")

        except KeyboardInterrupt:
            colors = ["\033[31m", "\033[33m", "\033[32m", "\033[34m", "\033[35m"]
            text = "👋🏻 程序已退出。客官走好，欢迎下次光临~"
            symbol = "👋🏻 "
            colored_text = symbol + "".join(f"{colors[i % len(colors)]}{char}\033[0m" for i, char in enumerate(text[len(symbol):]))
            print(f"\n{colored_text}")
            print("Open Source: https://github.com/Peaceful-World-X/PDF-PicKiller", end=" ")
            print(Fore.GREEN + "       公众号: 耗不尽的先生\n\n")
            sys.exit(0)


# 运行程序
if __name__ == "__main__":
    try:
        init()
        welcome_text = pyfiglet.figlet_format("PDF PicKiller", font="starwars", width=90, justify="center")
        print(welcome_text)
        print("Open Source: https://github.com/Peaceful-World-X/PDF-PicKiller", end=" ")
        print(Fore.GREEN + "       公众号: 耗不尽的先生\n\n\033[0m")
        main()
    except Exception as e:
        print(f"程序发生错误: {e}")
        time.sleep(10)  # 稍作停顿，便于查看错误信息
