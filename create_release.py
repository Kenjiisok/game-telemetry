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
    print(f"Version atualizada para {new_version}")
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
        'release_*.zip',
        'build',
        '*.spec',
        'KenjiOverlay_old.exe'
    }

    def should_exclude(path):
        path_str = str(path)
        for pattern in exclude_patterns:
            if pattern in path_str or path.name.startswith('.'):
                return True
        return False

    zip_filename = f"racing-telemetry-v{version}.zip"

    try:
        # Criar ZIP diretamente na raiz (para facilitar substituição)
        current_dir = Path.cwd()

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Adicionar executáveis (PRIORITÁRIO para auto-update)
            exe_files = ['dist/KenjiOverlay.exe', 'dist/updater.exe']
            for exe_file in exe_files:
                exe_path = current_dir / exe_file
                if exe_path.exists():
                    # Adicionar executáveis na raiz do ZIP
                    zipf.write(exe_path, exe_path.name)
                    print(f"  Incluído: {exe_path.name}")

            # Adicionar arquivos essenciais
            essential_files = [
                'version.py',
                'overlay.py',
                'tinypedal_inspired_overlay.py',
                'requirements.txt',
                'README.md'
            ]

            for file_name in essential_files:
                file_path = current_dir / file_name
                if file_path.exists():
                    zipf.write(file_path, file_name)
                    print(f"  Incluído: {file_name}")

            # Adicionar pasta src
            src_dir = current_dir / 'src'
            if src_dir.exists():
                for item in src_dir.rglob('*'):
                    if item.is_file() and not should_exclude(item):
                        arcname = item.relative_to(current_dir)
                        zipf.write(item, arcname)
                        print(f"  Incluído: {arcname}")

        print(f"Release ZIP criado: {zip_filename}")
        return zip_filename

    except Exception as e:
        print(f"Erro ao criar ZIP: {e}")
        return None

def print_github_instructions(version, zip_file, changelog):
    """Imprime instruções para criar release no GitHub"""
    print("\n" + "="*60)
    print("🚀 INSTRUÇÕES PARA CRIAR RELEASE NO GITHUB")
    print("="*60)
    print()
    print("1. Vá para: https://github.com/Kenjiisok/game-telemetry/releases/new")
    print()
    print(f"2. Tag version: v{version}")
    print(f"   Release title: Racing Telemetry v{version}")
    print()
    print("3. Description (changelog):")
    print("-" * 30)
    print(changelog)
    print("-" * 30)
    print()
    print("4. Faça upload dos arquivos:")
    print(f"   - {zip_file} (pacote completo)")
    print("   - dist/KenjiOverlay.exe (para auto-update)")
    print("   - dist/updater.exe (para auto-update)")
    print()
    print("5. Marque como 'Latest release' e clique 'Publish release'")
    print()
    print("="*60)
    print("AUTO-UPDATE:")
    print("   - Usuários com executável serão notificados automaticamente")
    print("   - Updates baixam apenas o KenjiOverlay.exe (mais rápido)")
    print("   - Substitui o executável e reinicia automaticamente")
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

    print(f"Criando release v{new_version}")
    print(f"Changelog: {changelog}")
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