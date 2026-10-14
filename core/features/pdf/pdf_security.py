import os
from typing import Optional
from pypdf import PdfReader, PdfWriter
from core.utils.logger import AppLogger, timed_operation


class PDFSecurity:
    """PDF 加密/解密工具"""

    def __init__(self):
        self.logger = AppLogger()
    
    @timed_operation("PDF 加密")
    def encrypt(self, pdf_path: str, output_path: str, user_password: str, 
                owner_password: Optional[str] = None, allow_printing: bool = False,
                allow_copying: bool = False) -> bool:
        """
        加密 PDF 文件
        
        :param pdf_path: 源 PDF 文件路径
        :param output_path: 输出 PDF 文件路径
        :param user_password: 用户密码（打开文档需要）
        :param owner_password: 所有者密码（修改权限需要，默认与用户密码相同）
        :param allow_printing: 是否允许打印
        :param allow_copying: 是否允许复制内容
        :return: 是否成功
        """
        try:
            self.logger.info(f"加密 PDF: {pdf_path} -> {output_path}")
            
            # 读取源 PDF
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            # 复制所有页面
            for page in reader.pages:
                writer.add_page(page)
            
            # 设置权限标志
            # 构建权限位掩码（基于 PDF 规范）
            permissions = 0
            
            # 基础权限：允许填写表单和辅助功能
            permissions |= (1 << 8)  # 填写表单
            permissions |= (1 << 9)  # 辅助功能提取
            
            if allow_printing:
                permissions |= (1 << 2)  # 允许打印
                permissions |= (1 << 11) # 允许高质量打印
            
            if allow_copying:
                permissions |= (1 << 4)  # 允许复制文本和图像
            
            # 加密
            writer.encrypt(
                user_password=user_password,
                owner_password=owner_password or user_password,
                permissions_flag=permissions
            )
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 保存加密后的文件
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            success_msg = f"加密成功: {os.path.basename(output_path)}"
            self.logger.info(success_msg)
            return True
            
        except Exception as e:
            error_msg = f"加密失败: {str(e)}"
            self.logger.error(error_msg)
            return False
    
    @timed_operation("PDF 解密")
    def decrypt(self, pdf_path: str, output_path: str, password: str) -> bool:
        """
        解密 PDF 文件
        
        :param pdf_path: 源 PDF 文件路径
        :param output_path: 输出 PDF 文件路径
        :param password: 解密密码
        :return: 是否成功
        """
        try:
            self.logger.info(f"解密 PDF: {pdf_path} -> {output_path}")
            
            # 读取加密的 PDF
            reader = PdfReader(pdf_path)
            
            # 检查是否加密
            if not reader.is_encrypted:
                self.logger.warning(f"PDF 文件未加密: {pdf_path}")
                # 直接复制文件
                import shutil
                shutil.copy2(pdf_path, output_path)
                return True
            
            # 解密
            if not reader.decrypt(password):
                error_msg = "密码错误"
                self.logger.error(f"解密失败: {error_msg}")
                return False
            
            # 创建新的 PDF（不加密）
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 保存解密后的文件
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            success_msg = f"解密成功: {os.path.basename(output_path)}"
            self.logger.info(success_msg)
            return True
            
        except Exception as e:
            error_msg = f"解密失败: {str(e)}"
            self.logger.error(error_msg)
            return False
    
    def batch_encrypt(self, files: list, password: str, output_dir: Optional[str] = None,
                     allow_printing: bool = False, allow_copying: bool = False):
        """
        批量加密 PDF 文件
        
        :param files: PDF 文件列表
        :param password: 加密密码
        :param output_dir: 输出目录（None 则在源文件目录创建 Encrypted 子目录）
        :param allow_printing: 是否允许打印
        :param allow_copying: 是否允许复制
        """
        total = len(files)
        success = 0
        fail = 0
        
        self.logger.info(f"开始批量加密 {total} 个文件")
        
        for i, file_path in enumerate(files):
            file_name = os.path.basename(file_path)
            
            # 确定输出路径
            if output_dir:
                output_path = os.path.join(output_dir, file_name)
            else:
                # 在源文件目录创建 Encrypted 子目录
                source_dir = os.path.dirname(file_path)
                encrypted_dir = os.path.join(source_dir, "Encrypted")
                os.makedirs(encrypted_dir, exist_ok=True)
                output_path = os.path.join(encrypted_dir, file_name)
            
            # 加密
            if self.encrypt(file_path, output_path, password, 
                           allow_printing=allow_printing, 
                           allow_copying=allow_copying):
                success += 1
            else:
                fail += 1
        
        self.logger.info(f"批量加密完成: 成功 {success} 个，失败 {fail} 个")
        return success, fail
    
    def batch_decrypt(self, files: list, password: str, output_dir: Optional[str] = None):
        """
        批量解密 PDF 文件
        
        :param files: PDF 文件列表
        :param password: 解密密码
        :param output_dir: 输出目录（None 则在源文件目录创建 Decrypted 子目录）
        """
        total = len(files)
        success = 0
        fail = 0
        
        self.logger.info(f"开始批量解密 {total} 个文件")
        
        for i, file_path in enumerate(files):
            file_name = os.path.basename(file_path)
            
            # 确定输出路径
            if output_dir:
                output_path = os.path.join(output_dir, file_name)
            else:
                # 在源文件目录创建 Decrypted 子目录
                source_dir = os.path.dirname(file_path)
                decrypted_dir = os.path.join(source_dir, "Decrypted")
                os.makedirs(decrypted_dir, exist_ok=True)
                output_path = os.path.join(decrypted_dir, file_name)
            
            # 解密
            if self.decrypt(file_path, output_path, password):
                success += 1
            else:
                fail += 1
        
        self.logger.info(f"批量解密完成: 成功 {success} 个，失败 {fail} 个")
        return success, fail