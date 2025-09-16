#!/usr/bin/env python3
"""
Updater Separado - Responsável por substituir o executável principal
Uso: updater.exe <download_url> <target_exe> <backup_name>
"""
import sys
import os
import time
import shutil
import tempfile
import zipfile
import subprocess
from pathlib import Path
from urllib.request import urlretrieve
import tkinter as tk
from tkinter import messagebox, ttk
import threading
# import psutil  # Removido - causava erro no PyInstaller

class StandaloneUpdater:
    def __init__(self, download_url, target_exe, backup_name):
        self.download_url = download_url
        self.target_exe = Path(target_exe)
        self.backup_name = backup_name

        # Criar janela de progresso
        self.root = tk.Tk()
        self.root.title("Atualizando Racing Telemetry...")
        self.root.geometry("400x150")
        self.root.resizable(False, False)

        # Centralizar janela
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (200)
        y = (self.root.winfo_screenheight() // 2) - (75)
        self.root.geometry(f"400x150+{x}+{y}")

        # Interface
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.status_label = ttk.Label(main_frame, text="Preparando atualização...")
        self.status_label.pack(pady=(0, 10))

        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        self.progress.start()

        self.detail_label = ttk.Label(main_frame, text="", font=("Arial", 8))
        self.detail_label.pack()

    def update_status(self, message, detail=""):
        """Atualiza status na interface"""
        self.status_label.config(text=message)
        self.detail_label.config(text=detail)
        self.root.update()

    def wait_for_process_end(self, process_name, timeout=30):
        """Aguarda um processo específico terminar (sem psutil)"""
        self.update_status("Aguardando aplicativo fechar...", f"Processo: {process_name}")

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Usar tasklist do Windows para verificar processo
            try:
                import subprocess
                result = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {process_name}'],
                                      capture_output=True, text=True, shell=True)
                if process_name.lower() not in result.stdout.lower():
                    return True
            except:
                # Se tasklist falhou, aguardar tempo fixo
                time.sleep(2)
                return True

            time.sleep(1)

        return False

    def download_update(self):
        """Baixa o arquivo de atualização"""
        try:
            self.update_status("Baixando atualização...", self.download_url)

            # Criar arquivo temporário
            temp_dir = tempfile.mkdtemp()

            # Verificar se é um ZIP ou executável direto
            if self.download_url.endswith('.zip'):
                # Baixar e extrair ZIP
                zip_path = os.path.join(temp_dir, "update.zip")
                urlretrieve(self.download_url, zip_path)

                self.update_status("Extraindo arquivos...")

                extract_dir = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                # Encontrar o executável
                new_exe = None
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.endswith('.exe') and 'KenjiOverlay' in file:
                            new_exe = os.path.join(root, file)
                            print(f"Debug: Encontrou executável: {file}")
                            break
                    if new_exe:
                        break

                if not new_exe:
                    # Listar todos os arquivos para debug
                    print("Debug: Arquivos encontrados no ZIP:")
                    for root, dirs, files in os.walk(extract_dir):
                        for file in files:
                            print(f"  - {file}")
                    raise Exception("Executável KenjiOverlay.exe não encontrado no arquivo de atualização")
            else:
                # Baixar executável diretamente
                new_exe = os.path.join(temp_dir, "KenjiOverlay.exe")
                urlretrieve(self.download_url, new_exe)

                if not os.path.exists(new_exe):
                    raise Exception("Falha ao baixar o executável")

            return new_exe, temp_dir

        except Exception as e:
            raise Exception(f"Erro ao baixar atualização: {str(e)}")

    def backup_current_exe(self):
        """Cria backup do executável atual"""
        try:
            if self.target_exe.exists():
                backup_path = self.target_exe.parent / self.backup_name
                self.update_status("Criando backup...", str(backup_path))
                shutil.copy2(self.target_exe, backup_path)
                return backup_path
        except Exception as e:
            print(f"Aviso: Não foi possível criar backup: {e}")
        return None

    def replace_executable(self, new_exe_path):
        """Substitui o executável principal"""
        try:
            self.update_status("Substituindo executável...", str(self.target_exe))

            # Aguardar processo terminar
            process_name = self.target_exe.name
            if not self.wait_for_process_end(process_name):
                # Tentar forçar fechamento com taskkill
                try:
                    subprocess.run(['taskkill', '/F', '/IM', process_name],
                                 capture_output=True, shell=True)
                    time.sleep(2)
                except:
                    pass

            # Aguardar um pouco mais para garantir
            time.sleep(2)

            # Criar backup
            backup_path = self.backup_current_exe()

            # Substituir arquivo
            shutil.copy2(new_exe_path, self.target_exe)

            self.update_status("Atualização concluída!", "Reiniciando aplicativo...")

            return True

        except Exception as e:
            # Tentar restaurar backup se falhou
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(backup_path, self.target_exe)
                except:
                    pass
            raise Exception(f"Erro ao substituir executável: {str(e)}")

    def restart_application(self):
        """Reinicia o aplicativo principal"""
        try:
            time.sleep(1)
            subprocess.Popen([str(self.target_exe)], cwd=str(self.target_exe.parent))
            return True
        except Exception as e:
            print(f"Erro ao reiniciar aplicativo: {e}")
            return False

    def run_update(self):
        """Executa o processo completo de atualização"""
        temp_dir = None
        try:
            # 1. Baixar atualização
            new_exe_path, temp_dir = self.download_update()

            # 2. Substituir executável
            self.replace_executable(new_exe_path)

            # 3. Reiniciar aplicativo
            if self.restart_application():
                self.update_status("✅ Atualização concluída!", "Aplicativo reiniciado com sucesso")
                time.sleep(2)
            else:
                self.update_status("⚠️ Atualização concluída", "Inicie o aplicativo manualmente")
                time.sleep(3)

            return True

        except Exception as e:
            self.progress.stop()
            messagebox.showerror("Erro na Atualização", str(e))
            return False

        finally:
            # Limpar arquivos temporários
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

def main():
    if len(sys.argv) != 4:
        print("Uso: updater.exe <download_url> <target_exe> <backup_name>")
        return 1

    download_url = sys.argv[1]
    target_exe = sys.argv[2]
    backup_name = sys.argv[3]

    updater = StandaloneUpdater(download_url, target_exe, backup_name)

    # Executar atualização em thread separada
    def run_update_thread():
        success = updater.run_update()
        updater.root.after(0, lambda: updater.root.destroy())

    threading.Thread(target=run_update_thread, daemon=True).start()

    # Mostrar interface
    updater.root.mainloop()

    return 0

if __name__ == "__main__":
    sys.exit(main())