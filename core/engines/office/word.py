import comtypes.client
from .base import BaseOfficeConverter

class WordEngine(BaseOfficeConverter):
    """Word 转 PDF 引擎"""
    
    # wdFormatPDF = 17
    WD_FORMAT_PDF = 17

    @property
    def app_name(self) -> str:
        return "Microsoft Word"

    def _create_app(self):
        # 使用 dynamic=True 以获得更好的兼容性
        app = comtypes.client.CreateObject("Word.Application", dynamic=True)
        try:
            # 保持 Word 不可见可以加快处理速度
            app.Visible = False
        except:
            pass
        return app

    def _open_document(self, app, file_path: str):
        return app.Documents.Open(file_path)

    def _save_as_pdf(self, doc, output_path: str):
        # 使用 ExportAsFixedFormat 替代 SaveAs2，兼容性更好
        doc.ExportAsFixedFormat(output_path, self.WD_FORMAT_PDF)

    def _close_document(self, doc):
        # 0 = wdDoNotSaveChanges
        doc.Close(0)

    def _quit_app(self, app):
        app.Quit()
