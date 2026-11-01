import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class NestedRepositoryTests(unittest.TestCase):
    source = Path(__file__).resolve().parents[1] / 'urace/portfolio.py'

    def git(self, root):
        root.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','init','-q',str(root)],check=True)

    def observed(self, source, cwd):
        script="import importlib.util,sys; s=importlib.util.spec_from_file_location('portfolio_fixture',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.ROOT)"
        return Path(subprocess.run([sys.executable,'-B','-c',script,str(source)],cwd=cwd,capture_output=True,text=True,check=True).stdout.strip())

    def test_nested_runtime_git_does_not_replace_product_root(self):
        with tempfile.TemporaryDirectory() as directory:
            product=Path(directory)/'project';runtime=product/'urace'
            self.git(product);self.git(runtime)
            source=runtime/'runtime/urace/portfolio.py';source.parent.mkdir(parents=True);shutil.copy2(self.source,source)
            self.assertEqual(self.observed(source,source.parent.parent),product)

    def test_installed_layout_wins_over_unrelated_current_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);product=root/'project';other=root/'unrelated'
            self.git(product);self.git(other)
            source=product/'urace/runtime/urace/portfolio.py';source.parent.mkdir(parents=True);shutil.copy2(self.source,source)
            self.assertEqual(self.observed(source,other),product)

    def test_standalone_helper_keeps_current_repository_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);product=root/'product';self.git(product)
            source=root/'helper.py';shutil.copy2(self.source,source)
            self.assertEqual(self.observed(source,product),product)
