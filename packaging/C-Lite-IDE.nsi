; C-Lite IDE - NSIS Installer Script
; Creates: C-Lite-IDE-Setup-<version>.exe
;
; Expected structure (relative to this script):
; project/
; ├── dist/
; │   └── C-Lite IDE/
; ├── icons/
; │   └── app.ico
; ├── LICENSE
; ├── README.md
; ├── packaging/
; │   └── C-Lite-IDE.nsi
; └── build_release.bat
;
; Usage:
;   makensis C-Lite-IDE.nsi
;   (Version is substituted by build_release.bat)

!include "MUI2.nsh"

; ------------------------------------------------------------
; Application information
; ------------------------------------------------------------

!define APP_NAME "C-Lite IDE"
!define APP_PUBLISHER "Nitin Raj"
!define APP_URL "https://github.com/17NitinRaj06/C-Lite-IDE"
!define APP_EXE "C-Lite IDE.exe"
!define APP_VERSION "1.1.1"

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

; Maximum compression. /SOLID treats all files as one compressed
; stream (much better ratio than per-file compression when you
; have many small files, e.g. a PyInstaller _internal folder).
SetCompressor /SOLID lzma
SetCompressorDictSize 64

; ------------------------------------------------------------
; File version information
; ------------------------------------------------------------

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=1033 "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey /LANG=1033 "FileDescription" "${APP_NAME} Installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Copyright © ${APP_PUBLISHER} 2026"

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

    ; Copy the complete built application including all subdirectories.
    SetOutPath "$INSTDIR"
    File /r "..\dist\C-Lite IDE\*"

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

    ; ------------------------------------------------------------
    ; File association ("Open with" candidate only — not default)
    ; ------------------------------------------------------------
    WriteRegStr HKCU "Software\Classes\Applications\${APP_EXE}\shell\open\command" "" '"$INSTDIR\${APP_EXE}" "%1"'
    WriteRegStr HKCU "Software\Classes\Applications\${APP_EXE}\SupportedTypes" ".c" ""
    WriteRegStr HKCU "Software\Classes\Applications\${APP_EXE}\SupportedTypes" ".cpp" ""
    WriteRegStr HKCU "Software\Classes\Applications\${APP_EXE}\SupportedTypes" ".cc" ""
    WriteRegStr HKCU "Software\Classes\Applications\${APP_EXE}\SupportedTypes" ".cxx" ""
    WriteRegStr HKCU "Software\Classes\Applications\${APP_EXE}\SupportedTypes" ".h" ""
    WriteRegStr HKCU "Software\Classes\Applications\${APP_EXE}\FriendlyAppName" "" "${APP_NAME}"
    System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, i 0, i 0)'

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
; Silent-install support (used by the in-app auto-updater, which
; runs "C-Lite-IDE-Setup-<version>.exe /S"). Normal double-click
; installs are unaffected and still show the full wizard.
;
; MUI_FINISHPAGE_RUN only relaunches the app from the Finish page,
; which silent installs skip entirely, so without this the app
; would install but never restart itself after an auto-update.
; ------------------------------------------------------------

Function .onInstSuccess
    IfSilent 0 +2
        Exec '"$INSTDIR\${APP_EXE}"'
FunctionEnd

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

    ; Remove file association registration.
    DeleteRegKey HKCU "Software\Classes\Applications\${APP_EXE}"
    System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, i 0, i 0)'

SectionEnd
