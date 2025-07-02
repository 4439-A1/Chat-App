import PyInstaller.__main__

PyInstaller.__main__.run([
    'code/clientapp.py',
    '--onefile',
    '--windowed',
    '--noconsole',
    '--name=ChatClient',
    '--icon=myicon.icns',
    '--hidden-import=tkinter',
    '--hidden-import=tkinter.simpledialog',
])