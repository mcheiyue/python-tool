import comtypes.client
from .base import BaseOfficeConverter

class ExcelEngine(BaseOfficeConverter):
    """Excel 转 PDF 引擎"""
    
    # xlTypePDF = 0
    XL_TYPE_PDF = 0

    @property
    def app_name(self) -> str:
        return "Microsoft Excel"

    def _create_app(self):
        app = comtypes.client.CreateObject("Excel.Application", dynamic=True)
        try:
            app.Visible = False
            app.DisplayAlerts = False
        except Exception:
            pass
        return app

    def _open_document(self, app, file_path: str):
        # Open(Filename, ReadOnly)
        return app.Workbooks.Open(file_path, ReadOnly=True)

    def _save_as_pdf(self, doc, output_path: str):
        doc.ExportAsFixedFormat(self.XL_TYPE_PDF, output_path)

    def _close_document(self, doc):
        # SaveChanges=False
        doc.Close(False)

    def _quit_app(self, app):
        app.Quit()
