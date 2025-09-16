#!/usr/bin/env python3
"""
Racing Telemetry Pedals - Overlay Principal
Ponto de entrada para o overlay com sistema de auto-update
"""
import sys
import os
import threading
import time

# Variável global para comunicar status de atualização
UPDATE_STATUS = {
    'has_update': False,
    'new_version': None,
    'checked': False
}

# Adicionar src/ ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from version import __version__, __app_name__
    print(f"{__app_name__} v{__version__}")
except ImportError:
    print("Racing Telemetry Pedals")

def check_updates_on_startup():
    """Verifica updates em background no startup"""
    try:
        print("Verificando atualizacoes em background...")

        # Verificar se temos acesso à internet
        try:
            from urllib.request import urlopen
            urlopen('https://github.com', timeout=5)
            print("Conexao com internet OK")
        except Exception as e:
            print(f"Sem conexao com internet: {e}")
            return

        from src.updater import check_updates_silent

        # Aguardar 3 segundos após startup para verificar updates
        print("Aguardando 3 segundos...")
        time.sleep(3)

        print("Consultando GitHub API...")
        has_update, new_version = check_updates_silent()
        print(f"Resultado: has_update={has_update}, new_version={new_version}")

        # Atualizar variável global
        UPDATE_STATUS['has_update'] = has_update
        UPDATE_STATUS['new_version'] = new_version
        UPDATE_STATUS['checked'] = True

        if has_update:
            print("="*60)
            print(f"NOVA VERSAO DISPONIVEL: v{new_version}")
            print("Use Ctrl+U para atualizar")
            print("="*60)

            # Mostrar notificação Windows nativa
            try:
                from win11toast import toast
                print("Enviando notificacao Windows...")
                result = toast(
                    'Racing Telemetry - Atualização Disponível!',
                    f'Nova versão v{new_version} disponível. Abra o aplicativo e pressione Ctrl+U para atualizar.',
                    audio='ms-winsoundevent:Notification.Default',
                    duration='long'
                )
                print(f"Notificacao Windows enviada! Resultado: {result}")
            except Exception as e:
                print(f"Erro ao enviar notificacao Windows: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("Aplicacao esta atualizada (versao mais recente)")

    except Exception as e:
        print(f"ERRO CRITICO ao verificar updates: {e}")
        import traceback
        print("Traceback completo:")
        traceback.print_exc()

def main():
    """Função principal"""
    print("Iniciando Racing Telemetry...")
    print(f"Debug: Executando como executável: {getattr(sys, 'frozen', False)}")

    # Verificar updates em background APENAS se executável
    if getattr(sys, 'frozen', False):
        print("Executavel detectado - iniciando verificacao de updates...")
        update_thread = threading.Thread(target=check_updates_on_startup, daemon=True)
        update_thread.start()
    else:
        print("Script Python detectado - pulando verificacao de updates")

    # Importar e executar o overlay principal
    try:
        # Importar o overlay principal
        import racing_overlay

        # Se o arquivo tem uma função main, executar
        if hasattr(racing_overlay, 'main'):
            racing_overlay.main()
        else:
            # Senão, importar e executar diretamente
            exec(open('racing_overlay.py').read())

    except FileNotFoundError:
        print("ERRO: Arquivo racing_overlay.py não encontrado!")
        print("Verifique se todos os arquivos estão presentes.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao iniciar overlay: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()