import os

# Ensure directories exist
for dir_name in ['sent', 'received']:
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)