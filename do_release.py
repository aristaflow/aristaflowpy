import subprocess
repository = 'testpypi'
#repository = 'pypi'

subprocess.call(['rm', '-rf', './dist/'])
subprocess.call(['python3', 'setup.py', 'install', 'sdist', 'bdist_wheel'])
subprocess.call(['python3','-m', 'twine', 'upload', '--repository', repository, 'dist/*'])
