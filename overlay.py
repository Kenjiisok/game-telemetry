#!/usr/bin/env python3
"""
Racing Telemetry Pedals - Overlay Principal
Ponto de entrada para o overlay com sistema de auto-update
"""
import sys
import os
import threading
import time

# Adicionar src/ ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from version import __version__, __app_name__
    print(f"🏎️ {__app_name__} v{__version__}")
except ImportError:
    print("🏎️ Racing Telemetry Pedals")

def check_updates_on_startup():
    """Verifica updates em background no startup"""
    try:
        print("🔍 Verificando atualizações em background...")
        from src.updater import check_updates_silent

        # Aguardar 3 segundos após startup para verificar updates
        time.sleep(3)

        has_update, new_version = check_updates_silent()
        print(f"Debug: has_update={has_update}, new_version={new_version}")

        if has_update:
            print(f"📦 NOVA VERSÃO DISPONÍVEL: v{new_version}")
            print("💡 Use Ctrl+U para atualizar")
            print("="*50)
        else:
            print("✅ Aplicação está atualizada")

    except Exception as e:
        print(f"⚠️ Erro ao verificar updates: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Função principal"""
    print("🚀 Iniciando Racing Telemetry...")
    print(f"Debug: Executando como executável: {getattr(sys, 'frozen', False)}")

    # Verificar updates em background APENAS se executável
    if getattr(sys, 'frozen', False):
        print("⚡ Executável detectado - iniciando verificação de updates...")
        update_thread = threading.Thread(target=check_updates_on_startup, daemon=True)
        update_thread.start()
    else:
        print("🐍 Script Python detectado - pulando verificação de updates")

    # Importar e executar o overlay principal
    try:
        # Importar o overlay principal
        import tinypedal_inspired_overlay

        # Se o arquivo tem uma função main, executar
        if hasattr(tinypedal_inspired_overlay, 'main'):
            tinypedal_inspired_overlay.main()
        else:
            # Senão, importar e executar diretamente
            exec(open('tinypedal_inspired_overlay.py').read())

    except FileNotFoundError:
        print("❌ Arquivo tinypedal_inspired_overlay.py não encontrado!")
        print("Verifique se todos os arquivos estão presentes.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao iniciar overlay: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()