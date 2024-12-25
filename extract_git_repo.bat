@echo off
setlocal enabledelayedexpansion

rem Set the source directory containing the .git folders
set "sourceDir=.\0x2196f3"

rem Set the destination directory for the cloned repositories
set "destDir=%USERPROFILE%\Desktop\repobackup"

rem Create the destination directory if it doesn't exist
if not exist "%destDir%" (
    mkdir "%destDir%"
)

for /d %%D in ("%sourceDir%\*.git") do (
    rem Get the name of the repository from the path
    set "repoName=%%~nxD"

    rem Clone the repository into the destination directory
    git clone "%%D" "%destDir%\!repoName!"
)

echo All repositories have been cloned to %destDir%.
pause