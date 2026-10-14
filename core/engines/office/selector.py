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
    # 1. 优先尝试 MS Office（如果可用）
    try:
        if engine_type == 'word':
            from core.engines.office import WordEngine
            return WordEngine()
        elif engine_type == 'excel':
            from core.engines.office import ExcelEngine
            return ExcelEngine()
        elif engine_type == 'powerpoint':
            from core.engines.office import PowerPointEngine
            return PowerPointEngine()
        else:
            raise ValueError(f"Unknown engine type: {engine_type}")

    except Exception:
        # MS Office 不可用，尝试 LibreOffice
        pass

    # 2. 降级到 LibreOffice
    libreoffice_tool = tool_manager.get_tool("libreoffice")

    if libreoffice_tool and libreoffice_tool.is_available():
        from core.engines.office.libreoffice import LibreOfficeEngine
        return LibreOfficeEngine()

    # 3. 都不可用，返回 MS Office 引擎（会在使用时报错）
    # 这样可以保持一致的错误处理流程
    if engine_type == 'word':
        from core.engines.office import WordEngine
        return WordEngine()
    elif engine_type == 'excel':
        from core.engines.office import ExcelEngine
        return ExcelEngine()
    else:
        from core.engines.office import PowerPointEngine
        return PowerPointEngine()
