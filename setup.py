from distutils.core import setup
import py2exe
import os

# Ensure directories exist
for dir_name in ['sent', 'received']:
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

setup(
    name="FileTransfer",
    version="1.0",
    description="File Transfer Application",
    author="FileTransfer",
    
    options = {
        'py2exe': {
            'compressed': True,
            'optimize': 2,
            'includes': [
                'tkinter', 
                'tkinter.ttk',
                'socket',
                'threading',
                'datetime',
                'shutil',
                'os'
            ],
            'exclude_dlls': ['w9xpopen.exe', 'MSVCP90.dll'],
            'dist_dir': 'dist',
        }
    },
    windows = [{'script': 'file_transfer.py'}],
)