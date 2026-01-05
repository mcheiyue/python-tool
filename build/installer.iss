; Office Toolkit 安装脚本
; 支持三种模式: 安装版、绿化版、便携版

#define MyAppName "Office Toolkit"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "OfficeToolkit Team"
#define MyAppExeName "OfficeToolkit.exe"

[Setup]
; 应用标识 (不要修改 GUID)
AppId={{A35B6F8C-7E4D-4F2A-9B3C-1D5E6F7A8B9C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; 输出目录
OutputDir=..\release
OutputBaseFilename=OfficeToolkit_Setup_v{#MyAppVersion}
; 压缩设置
Compression=lzma2/ultra64
SolidCompression=yes
; 图标
SetupIconFile=..\assets\processed_icons\icon_transparent.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; 架构
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
; 界面风格
WizardStyle=modern

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 主程序
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; 插件包 (Ghostscript.mcy, Pandoc.mcy)
Source: "..\plugins\*"; DestDir: "{app}\plugins"; Flags: ignoreversion recursesubdirs createallsubdirs
; 预解压的依赖库 (可选)
Source: "..\libs\*"; DestDir: "{app}\libs"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
; 配置文件 (默认配置)
Source: "..\config\default.json"; DestDir: "{app}\config"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
