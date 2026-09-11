import os
import sys
import PyInstaller.__main__

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(BASE_DIR, "comic_reader.py")
APP_ICON = os.path.join(BASE_DIR, "icons", "app.ico")
ICONS_DIR = os.path.join(BASE_DIR, "icons")

def build():
    if not os.path.isfile(APP_ICON):
        print(f"Error: Could not find app icon at: {APP_ICON}")
        return

    pyinstaller_args = [
        SCRIPT_PATH,
        "--name=ComicReader",
        "--noconsole",
        "--onedir",            # Directory output instead of single-file extraction
        "--clean",
        f"--icon={APP_ICON}",
        f"--add-data={ICONS_DIR}{os.pathsep}icons",
    ]

    for tool_name in ["UnRAR.exe", "7z.exe"]:
        tool_path = os.path.join(BASE_DIR, tool_name)
        if os.path.isfile(tool_path):
            pyinstaller_args.append(f"--add-binary={tool_path}{os.pathsep}.")

    print("Building ComicReader with --onedir...")
    PyInstaller.__main__.run(pyinstaller_args)
    print("\nBuild finished! Application folder located at: dist/ComicReader")

if __name__ == "__main__":
    build()