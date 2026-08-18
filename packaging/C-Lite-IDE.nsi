; C-Lite IDE - NSIS Installer Script
; Creates: C-Lite-IDE-Setup-<version>.exe
;
; Expected structure:
; project/
; ├── dist/
; │   └── C-Lite IDE/
; ├── icons/
; │   └── app.ico
; ├── LICENSE
; ├── README.md
; ├── installer/
; │   └── C-Lite-IDE.nsi
; └── build_release.bat
;
; Usage:
;   makensis C-Lite-IDE.nsi
;
; VERSION_PLACEHOLDER is replaced by build_release.bat.

!include "MUI2.nsh"

; ------------------------------------------------------------
; Application information
; ------------------------------------------------------------

!define APP_NAME "C-Lite IDE"
!define APP_PUBLISHER "C-Lite"
!define APP_URL "https://github.com/YOUR_GITHUB_USERNAME/C-Lite-IDE"
!define APP_EXE "C-Lite IDE.exe"
!define APP_VERSION "VERSION_PLACEHOLDER"

; ------------------------------------------------------------
; Installer configuration
; ------------------------------------------------------------

Name "${APP_NAME}"
OutFile "..\release\C-Lite-IDE-Setup-${APP_VERSION}.exe"

; Per-user installation: no administrator privileges required.
InstallDir "$LOCALAPPDATA\${APP_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" "InstallDir"

RequestExecutionLevel user
Unicode True

Icon "..\icons\app.ico"

; ------------------------------------------------------------
; File version information
; ------------------------------------------------------------

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=1033 "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey /LANG=1033 "FileDescription" "${APP_NAME} Installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Copyright © ${APP_PUBLISHER}"

; ------------------------------------------------------------
; Modern UI
; ------------------------------------------------------------

!define MUI_ABORTWARNING
!define MUI_ICON "..\icons\app.ico"
!define MUI_UNICON "..\icons\app.ico"

!define MUI_WELCOMEPAGE_TITLE "Welcome to ${APP_NAME}"
!define MUI_WELCOMEPAGE_TEXT \
"Setup will install ${APP_NAME} ${APP_VERSION} on your computer.$\r$\n$\r$\nClick Next to continue."

!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ------------------------------------------------------------
; Main installation
; ------------------------------------------------------------

Section "C-Lite IDE" SecMain

    SectionIn RO

    ; Copy the complete built application.
    SetOutPath "$INSTDIR"
    File /r "..\dist\C-Lite IDE\*.*"

    ; Store installation information.
    WriteRegStr HKCU "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\${APP_NAME}" "Version" "${APP_VERSION}"

    ; Create Start Menu folder.
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"

    ; Start Menu shortcut.
    CreateShortCut \
        "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" \
        "" \
        "$INSTDIR\icons\app.ico"

    ; Start Menu uninstall shortcut.
    CreateShortCut \
        "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" \
        "$INSTDIR\Uninstall.exe" \
        "" \
        "$INSTDIR\icons\app.ico"

    ; Desktop shortcut.
    CreateShortCut \
        "$DESKTOP\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" \
        "" \
        "$INSTDIR\icons\app.ico"

    ; Create uninstaller.
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Windows uninstall information.
    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\C-Lite-IDE" \
        "DisplayName" "${APP_NAME}"

    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\C-Lite-IDE" \
        "DisplayVersion" "${APP_VERSION}"

    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\C-Lite-IDE" \
        "Publisher" "${APP_PUBLISHER}"

    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\C-Lite-IDE" \
        "URLInfoAbout" "${APP_URL}"

    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\C-Lite-IDE" \
        "UninstallString" "$INSTDIR\Uninstall.exe"

    WriteRegStr HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\C-Lite-IDE" \
        "DisplayIcon" "$INSTDIR\icons\app.ico"

SectionEnd

; ------------------------------------------------------------
; Uninstallation
; ------------------------------------------------------------

Section "Uninstall"

    ; Remove shortcuts.
    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"

    RMDir "$SMPROGRAMS\${APP_NAME}"

    ; Remove installed files.
    RMDir /r "$INSTDIR"

    ; Remove registry entries.
    DeleteRegKey HKCU "Software\${APP_NAME}"
    DeleteRegKey HKCU \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\C-Lite-IDE"

SectionEnd
