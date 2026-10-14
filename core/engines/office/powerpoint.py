import comtypes.client
from .base import BaseOfficeConverter

class PowerPointEngine(BaseOfficeConverter):
    """PowerPoint 转 PDF 引擎"""
    
    # ppSaveAsPDF = 32
    PP_SAVE_AS_PDF = 32

    @property
    def app_name(self) -> str:
        return "Microsoft PowerPoint"

    def _create_app(self):
        app = comtypes.client.CreateObject("PowerPoint.Application", dynamic=True)
        try:
            # PowerPoint 需要可见才能正常工作
            app.Visible = 1
            # 最小化窗口
            app.WindowState = 2 
        except Exception:
            pass
        return app

    def _open_document(self, app, file_path: str):
        # Open(FileName, ReadOnly, Untitled, WithWindow)
        return app.Presentations.Open(file_path, True, False, False)

    def _save_as_pdf(self, doc, output_path: str):
        doc.SaveAs(output_path, self.PP_SAVE_AS_PDF)

    def _close_document(self, doc):
        doc.Close()

    def _quit_app(self, app):
        app.Quit()
