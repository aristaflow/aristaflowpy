# Default Python Libraries
import subprocess


repository = "testpypi"
# repository = 'pypi'

subprocess.call(["rm", "-rf", "./dist/"])
subprocess.call(["python3", "-m", "build"])
subprocess.call(["python3", "-m", "twine", "upload", "--repository", repository, "dist/*"])
