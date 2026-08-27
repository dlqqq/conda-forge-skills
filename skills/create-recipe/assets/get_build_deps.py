#!/usr/bin/env python3
import sys
import json
import urllib.request
import tarfile
import zipfile
import tempfile
from pathlib import Path

def get_build_deps(package_name, version=None):
    # Get package metadata
    url = f"https://pypi.org/pypi/{package_name}/json"
    with urllib.request.urlopen(url) as response:
        data = json.load(response)
    
    # Use specified version or latest
    if version is None:
        version = data['info']['version']
    
    # Find source distribution
    releases = data['releases'].get(version, [])
    sdist_url = None
    for release in releases:
        if release['packagetype'] == 'sdist':
            sdist_url = release['url']
            break
    
    if not sdist_url:
        print(f"No source distribution found for {package_name} {version}")
        return None
    
    # Download and extract
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        sdist_path = tmpdir / "package.tar.gz"
        
        with urllib.request.urlopen(sdist_url) as response:
            sdist_path.write_bytes(response.read())
        
        # Extract
        if sdist_path.suffix == '.gz':
            with tarfile.open(sdist_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
        else:
            with zipfile.ZipFile(sdist_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
        
        # Find pyproject.toml
        pyproject_files = list(tmpdir.rglob('pyproject.toml'))
        if not pyproject_files:
            print("No pyproject.toml found")
            return None
        
        pyproject_path = pyproject_files[0]
        
        # Parse TOML
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        
        with open(pyproject_path, 'rb') as f:
            config = tomllib.load(f)
        
        result = {}
        
        # Get build-system.requires
        if 'build-system' in config and 'requires' in config['build-system']:
            result['build-system.requires'] = config['build-system']['requires']
        
        # Get tool.hatch.build.hooks.jupyter-builder.dependencies
        try:
            deps = config['tool']['hatch']['build']['hooks']['jupyter-builder']['dependencies']
            result['tool.hatch.build.hooks.jupyter-builder.dependencies'] = deps
        except KeyError:
            pass
        
        return result

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python get_build_deps.py PACKAGE_NAME [VERSION]")
        sys.exit(1)
    
    package = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else None
    
    deps = get_build_deps(package, version)
    if deps:
        print(json.dumps(deps, indent=2))
