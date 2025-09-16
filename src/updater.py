import json
import os
import sys
import tempfile
import zipfile
import shutil
import time
import subprocess
import threading
from pathlib import Path
from urllib.request import urlopen, urlretrieve
import tkinter as tk
from tkinter import messagebox, ttk

from version import __version__, __github_repo__

class AutoUpdater:
    def __init__(self):
        self.current_version = __version__
        self.repo = __github_repo__
        self.api_url = f"https://api.github.com/repos/{self.repo}/releases/latest"

    def check_for_updates(self, silent=False):
        """Verifica se há uma nova versão disponível"""
        try:
            with urlopen(self.api_url) as response:
                data = json.loads(response.read().decode())

            latest_version = data['tag_name'].lstrip('v')
            download_url = None

            # Procurar primeiro por executável (prioridade para auto-update)
            for asset in data['assets']:
                if asset['name'] == 'KenjiOverlay.exe':
                    download_url = asset['browser_download_url']
                    break

            # Se não encontrou executável, procurar por ZIP
            if not download_url:
                for asset in data['assets']:
                    if asset['name'].endswith('.zip'):
                        download_url = asset['browser_download_url']
                        print(f"Debug: Usando ZIP para update: {asset['name']}")
                        break

            if self._is_newer_version(latest_version, self.current_version):
                if not silent:
                    return self._show_update_dialog(latest_version, download_url, data.get('body', ''))
                return True, latest_version, download_url
            else:
                if not silent:
                    messagebox.showinfo("Atualização", "Você já tem a versão mais recente!")
                return False, None, None

        except Exception as e:
            if not silent:
                messagebox.showerror("Erro", f"Erro ao verificar atualizações: {str(e)}")
            return False, None, None

    def _is_newer_version(self, latest, current):
        """Compara versões (formato x.y.z)"""
        def version_tuple(v):
            return tuple(map(int, v.split('.')))
        return version_tuple(latest) > version_tuple(current)

    def _show_update_dialog(self, new_version, download_url, changelog):
        """Mostra dialog perguntando se quer atualizar"""
        root = tk.Tk()
        root.title("Atualização Disponível")
        root.geometry("500x400")
        root.resizable(False, False)

        # Centralizar janela
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (500 // 2)
        y = (root.winfo_screenheight() // 2) - (400 // 2)
        root.geometry(f"500x400+{x}+{y}")

        result = {'update': False}

        # Frame principal
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título
        title_label = ttk.Label(main_frame, text="Nova versao disponivel!",
                               font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 10))

        # Info da versão
        version_frame = ttk.Frame(main_frame)
        version_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(version_frame, text=f"Versão atual: {self.current_version}").pack(anchor=tk.W)
        ttk.Label(version_frame, text=f"Nova versão: {new_version}",
                 font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)

        # Changelog
        ttk.Label(main_frame, text="O que há de novo:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))

        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        changelog_text = tk.Text(text_frame, wrap=tk.WORD, height=8)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=changelog_text.yview)
        changelog_text.configure(yscrollcommand=scrollbar.set)

        changelog_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        changelog_text.insert(tk.END, changelog or "Sem informações de changelog disponíveis.")
        changelog_text.configure(state=tk.DISABLED)

        # Botões
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        def update_now():
            result['update'] = True
            root.destroy()

        def later():
            root.destroy()

        ttk.Button(button_frame, text="Atualizar Agora", command=update_now).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Mais Tarde", command=later).pack(side=tk.RIGHT)

        root.mainloop()

        if result['update']:
            self._download_and_install(download_url)

        return result['update']

    def _download_and_install(self, download_url):
        """Baixa e instala a atualização"""
        # Detectar se está rodando como executável
        if getattr(sys, 'frozen', False):
            # Rodando como executável - usar updater separado
            self._use_external_updater(download_url)
        else:
            # Rodando como script Python - método tradicional
            self._traditional_update(download_url)

    def _use_external_updater(self, download_url):
        """Usa o updater.exe separado para atualizar"""
        try:
            import sys

            # Path do executável atual
            current_exe = sys.executable

            # Path do updater (deve estar na mesma pasta)
            updater_path = os.path.join(os.path.dirname(current_exe), "updater.exe")

            if not os.path.exists(updater_path):
                messagebox.showerror("Erro", "Arquivo updater.exe não encontrado!")
                return

            # Nome do backup
            backup_name = f"KenjiOverlay_backup_{int(time.time())}.exe"

            # Mostrar mensagem
            messagebox.showinfo("Atualização",
                "O updater será executado.\n"
                "O aplicativo será fechado e reiniciado automaticamente.")

            # Encontrar URL do executável específico
            exe_download_url = self._get_exe_download_url(download_url)

            # Executar updater
            subprocess.Popen([
                updater_path,
                exe_download_url or download_url,
                current_exe,
                backup_name
            ])

            # Fechar aplicativo atual após delay
            time.sleep(1)
            sys.exit(0)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao executar updater: {str(e)}")

    def _get_exe_download_url(self, download_url):
        """Retorna a URL correta para download (executável ou ZIP)"""
        try:
            # Se já é uma URL de executável, retornar como está
            if download_url.endswith('.exe'):
                print(f"Debug: URL é executável direto: {download_url}")
                return download_url

            # Verificar se existe executável individual na release
            with urlopen(self.api_url) as response:
                data = json.loads(response.read().decode())

            # Procurar por executável individual
            for asset in data['assets']:
                if asset['name'] == 'KenjiOverlay.exe':
                    print(f"Debug: Encontrado executável individual: {asset['browser_download_url']}")
                    return asset['browser_download_url']

            # Se não encontrou executável individual, usar ZIP
            print(f"Debug: Executável individual não encontrado, usando ZIP: {download_url}")
            return download_url

        except Exception as e:
            print(f"Aviso: Erro ao verificar assets: {e}")
            return download_url

    def _traditional_update(self, download_url):
        """Método tradicional para script Python"""
        progress_window = tk.Tk()
        progress_window.title("Atualizando...")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)

        # Centralizar
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (150 // 2)
        progress_window.geometry(f"400x150+{x}+{y}")

        main_frame = ttk.Frame(progress_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        status_label = ttk.Label(main_frame, text="Baixando atualização...")
        status_label.pack(pady=(0, 10))

        progress = ttk.Progressbar(main_frame, mode='indeterminate')
        progress.pack(fill=tk.X, pady=(0, 10))
        progress.start()

        def update_in_background():
            try:
                # Criar diretório temporário
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_path = os.path.join(temp_dir, "update.zip")

                    # Baixar arquivo
                    urlretrieve(download_url, zip_path)

                    status_label.config(text="Extraindo arquivos...")

                    # Extrair ZIP
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)

                    status_label.config(text="Instalando atualização...")

                    # Encontrar pasta extraída
                    extracted_folder = None
                    for item in os.listdir(temp_dir):
                        item_path = os.path.join(temp_dir, item)
                        if os.path.isdir(item_path) and item != "__pycache__":
                            extracted_folder = item_path
                            break

                    if extracted_folder:
                        # Atualizar arquivos Python
                        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

                        # Copiar arquivos atualizados
                        import shutil
                        for item in os.listdir(extracted_folder):
                            src = os.path.join(extracted_folder, item)
                            dst = os.path.join(current_dir, item)

                            if os.path.isfile(src) and src.endswith('.py'):
                                shutil.copy2(src, dst)

                        progress_window.after(0, lambda: [
                            progress_window.destroy(),
                            messagebox.showinfo("Sucesso", "Atualização instalada! Reinicie o aplicativo."),
                        ])
                    else:
                        raise Exception("Estrutura de arquivo inválida na atualização")

            except Exception as e:
                progress_window.after(0, lambda: [
                    progress_window.destroy(),
                    messagebox.showerror("Erro", f"Erro durante a atualização: {str(e)}")
                ])

        # Executar download em thread separada
        threading.Thread(target=update_in_background, daemon=True).start()
        progress_window.mainloop()

    def _create_update_script(self, source_folder):
        """Cria script para copiar arquivos novos"""
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_content = f'''@echo off
echo Atualizando Racing Telemetry...
timeout /t 3 /nobreak >nul

echo Copiando arquivos...
xcopy /E /Y "{source_folder}\\*" "{current_dir}\\"

echo Limpando arquivos temporários...
del /q "%~f0"

echo Iniciando aplicativo...
cd /d "{current_dir}"
python overlay.py

exit
'''

        script_path = os.path.join(tempfile.gettempdir(), "update_racing_telemetry.bat")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        # Executar script
        subprocess.Popen(script_path, shell=True)

    def _restart_app(self):
        """Reinicia o aplicativo"""
        sys.exit(0)

def check_updates_silent():
    """Função para verificar updates silenciosamente no startup"""
    updater = AutoUpdater()
    has_update, version, url = updater.check_for_updates(silent=True)
    return has_update, version

def show_update_dialog():
    """Função para mostrar dialog de atualização manualmente"""
    updater = AutoUpdater()
    updater.check_for_updates(silent=False)

if __name__ == "__main__":
    show_update_dialog()