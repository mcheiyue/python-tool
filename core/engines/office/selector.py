from core.external_tools.manager import ExternalToolManager


def create_office_engine(engine_type: str, tool_manager: ExternalToolManager):
    """
    创建 Office 引擎（自动选择 MS Office 或 LibreOffice）

    Args:
        engine_type: 'word', 'excel', 或 'powerpoint'
        tool_manager: 外部工具管理器（读取 LibreOffice 状态用）

    Returns:
        适用的引擎实例
    """
    # 后端是否可用须在转换线程实际连接后判断，构造阶段不启动 Office 或下载工具。
    if engine_type == 'word':
        from core.engines.office import WordEngine
        return WordEngine(tool_manager)
    elif engine_type == 'excel':
        from core.engines.office import ExcelEngine
        return ExcelEngine(tool_manager)
    elif engine_type == 'powerpoint':
        from core.engines.office import PowerPointEngine
        return PowerPointEngine(tool_manager)
    raise ValueError(f"Unknown engine type: {engine_type}")
