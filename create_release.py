#!/usr/bin/env python3
"""
Script para criar release automaticamente no GitHub.
Uso: python create_release.py [nova_versao] [mensagem_changelog]

Exemplo: python create_release.py 1.1.0 "Corrigido bug de conexão UDP"
"""

import os
import sys
import zipfile
import shutil
import tempfile
from pathlib import Path
import re

def update_version_file(new_version):
    """Atualiza o arquivo version.py com a nova versão"""
    version_file = Path("version.py")
    if not version_file.exists():
        print("❌ Arquivo version.py não encontrado!")
        return False

    content = version_file.read_text(encoding='utf-8')
    new_content = re.sub(
        r'__version__ = "[^"]*"',
        f'__version__ = "{new_version}"',
        content
    )

    version_file.write_text(new_content, encoding='utf-8')
    print(f"✅ Version atualizada para {new_version}")
    return True

def create_release_zip(version):
    """Cria arquivo ZIP para release"""
    exclude_patterns = {
        '__pycache__',
        '.git',
        '.gitignore',
        '.vscode',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.DS_Store',
        'Thumbs.db',
        'create_release.py',
        'release_*.zip'
    }

    def should_exclude(path):
        path_str = str(path)
        for pattern in exclude_patterns:
            if pattern in path_str or path.name.startswith('.'):
                return True
        return False

    zip_filename = f"racing-telemetry-v{version}.zip"
    temp_dir = Path(tempfile.mkdtemp())
    release_dir = temp_dir / f"racing-telemetry-{version}"

    try:
        # Copiar arquivos para diretório temporário
        current_dir = Path.cwd()
        release_dir.mkdir()

        for item in current_dir.rglob('*'):
            if should_exclude(item):
                continue

            relative_path = item.relative_to(current_dir)
            target_path = release_dir / relative_path

            if item.is_file():
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_path)

        # Criar ZIP
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in release_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(release_dir)
                    zipf.write(file_path, arcname)

        print(f"✅ Release ZIP criado: {zip_filename}")
        return zip_filename

    finally:
        # Limpar diretório temporário
        shutil.rmtree(temp_dir, ignore_errors=True)

def print_github_instructions(version, zip_file, changelog):
    """Imprime instruções para criar release no GitHub"""
    print("\n" + "="*60)
    print("🚀 INSTRUÇÕES PARA CRIAR RELEASE NO GITHUB")
    print("="*60)
    print()
    print("1. Vá para: https://github.com/SEU-USUARIO/game-telemetry/releases/new")
    print()
    print(f"2. Tag version: v{version}")
    print(f"   Release title: Racing Telemetry v{version}")
    print()
    print("3. Description (changelog):")
    print("-" * 30)
    print(changelog)
    print("-" * 30)
    print()
    print(f"4. Faça upload do arquivo: {zip_file}")
    print()
    print("5. Marque como 'Latest release' e clique 'Publish release'")
    print()
    print("="*60)
    print("⚠️  IMPORTANTE: Atualize o arquivo version.py com o nome do seu repositório!")
    print("    Edite a linha: __github_repo__ = \"seu-usuario/game-telemetry\"")
    print("="*60)

def main():
    if len(sys.argv) < 2:
        print("Uso: python create_release.py [versao] [changelog]")
        print("Exemplo: python create_release.py 1.1.0 'Corrigido bug de conexão'")
        return

    new_version = sys.argv[1]
    changelog = sys.argv[2] if len(sys.argv) > 2 else "Atualizações e melhorias"

    # Validar formato da versão
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print("❌ Formato de versão inválido! Use: x.y.z (ex: 1.0.0)")
        return

    print(f"📦 Criando release v{new_version}")
    print(f"📝 Changelog: {changelog}")
    print()

    # Atualizar versão
    if not update_version_file(new_version):
        return

    # Criar ZIP
    zip_file = create_release_zip(new_version)

    # Mostrar instruções
    print_github_instructions(new_version, zip_file, changelog)

if __name__ == "__main__":
    main()