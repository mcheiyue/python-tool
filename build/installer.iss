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
; 打包整个 standalone 目录（包含所有依赖）
Source: "..\dist\release\main.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 确保 plugins 目录存在并包含说明文件
Source: "..\plugins\README.txt"; DestDir: "{app}\plugins"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
