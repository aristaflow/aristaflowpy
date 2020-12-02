# Default Python Libraries
import os
import subprocess


repository = "testpypi"
# repository = 'pypi'

libs = os.listdir("./swagger/")
for lib in libs:
    subprocess.call(
        ["python3", "-m", "twine", "upload", "--repository", repository, "dist/*"],
        cwd=f"swagger/{lib}",
    )
