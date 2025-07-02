import PyInstaller.__main__

PyInstaller.__main__.run([
    'code/clientapp.py',
    '--onefile',
    '--windowed',
    '--noconsole',
    '--name=ChatClient',
    '--hidden-import=tkinter',
    '--hidden-import=tkinter.simpledialog',
])