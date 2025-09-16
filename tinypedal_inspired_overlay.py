"""
TinyPedal-Inspired Overlay
Baseado na análise do projeto TinyPedal (projeto real que funciona)
Usa PySide/Qt em vez de pygame para overlay REAL
"""
import sys
import os
import time
import math
import threading

# Verificar se PySide está disponível
try:
    from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QProgressBar
    from PySide6.QtCore import Qt, QTimer, Signal, QPoint
    from PySide6.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush, QPolygon
    PYSIDE_VERSION = "PySide6"
except ImportError:
    try:
        from PySide2.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QProgressBar
        from PySide2.QtCore import Qt, QTimer, Signal, QPoint
        from PySide2.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush, QPolygon
        PYSIDE_VERSION = "PySide2"
    except ImportError:
        print("ERROR: Nem PySide6 nem PySide2 estao instalados!")
        print("Instale com: pip install PySide6")
        sys.exit(1)

class RealPedalReader:
    """Leitor REAL de pedais usando pygame (compatível com G920, etc)"""
    def __init__(self):
        self.throttle = 0.0
        self.brake = 0.0
        self.connected = False
        self.running = False
        self.thread = None
        self.joysticks = []

        # Configuração de mapeamento
        self.throttle_axis = None
        self.brake_axis = None
        self.throttle_joystick = None
        self.brake_joystick = None

    def start(self):
        """Inicia leitura REAL de pedais"""
        print(f"  Iniciando leitor REAL de pedais...")

        try:
            # Importar pygame aqui para não interferir com Qt
            import pygame

            # Inicializar apenas joystick
            pygame.init()
            pygame.joystick.init()

            # Detectar dispositivos
            joystick_count = pygame.joystick.get_count()
            print(f"    Dispositivos encontrados: {joystick_count}")

            if joystick_count == 0:
                print("    Nenhum pedal/volante encontrado - usando dados simulados")
                return self._start_simulation()

            # Inicializar dispositivos
            for i in range(joystick_count):
                joystick = pygame.joystick.Joystick(i)
                joystick.init()
                self.joysticks.append(joystick)

                print(f"    {i}: {joystick.get_name()}")
                print(f"       Eixos: {joystick.get_numaxes()}")

            # Auto-detectar configuração
            self._auto_detect_pedals()

            # Iniciar thread de leitura REAL
            self.connected = True
            self.running = True
            self.thread = threading.Thread(target=self._real_read_loop, daemon=True)
            self.thread.start()

            print(f"    Pedais REAIS conectados!")
            return True

        except Exception as e:
            print(f"    Erro nos pedais: {e}")
            print(f"    Fallback para dados simulados")
            return self._start_simulation()

    def _auto_detect_pedals(self):
        """Auto-detecta configuração dos pedais (baseado no código existente)"""
        if len(self.joysticks) >= 1:
            main_device = self.joysticks[0]
            axes_count = main_device.get_numaxes()
            device_name = main_device.get_name().lower()

            print(f"    Configurando: {main_device.get_name()}")

            # Configuração específica para G920/Logitech
            if "g920" in device_name or "logitech" in device_name:
                print("      Detectado: Logitech G920")
                self.throttle_joystick = main_device
                self.brake_joystick = main_device
                self.throttle_axis = 1  # Eixo 1 = Acelerador no G920
                self.brake_axis = 2     # Eixo 2 = Freio no G920

            elif axes_count >= 2:
                # Configuração genérica
                print("      Usando configuração genérica")
                self.throttle_joystick = main_device
                self.brake_joystick = main_device
                self.throttle_axis = 1
                self.brake_axis = 2

            elif axes_count == 1:
                print("      Apenas 1 eixo - usando para throttle")
                self.throttle_joystick = main_device
                self.throttle_axis = 0

    def _real_read_loop(self):
        """Loop de leitura REAL dos pedais"""
        import pygame

        while self.running:
            try:
                pygame.event.pump()  # Atualiza eventos

                # Ler throttle
                new_throttle = 0.0
                if self.throttle_joystick and self.throttle_axis is not None:
                    if self.throttle_axis < self.throttle_joystick.get_numaxes():
                        raw_throttle = self.throttle_joystick.get_axis(self.throttle_axis)
                        new_throttle = self._normalize_axis(raw_throttle)

                # Ler brake
                new_brake = 0.0
                if self.brake_joystick and self.brake_axis is not None:
                    if self.brake_axis < self.brake_joystick.get_numaxes():
                        raw_brake = self.brake_joystick.get_axis(self.brake_axis)
                        new_brake = self._normalize_axis(raw_brake)

                # Atualizar valores
                self.throttle = new_throttle
                self.brake = new_brake

                time.sleep(0.016)  # ~60fps

            except Exception as e:
                if self.running:
                    print(f"    Erro lendo pedais: {e}")
                    time.sleep(0.1)

    def _normalize_axis(self, raw_value):
        """Normaliza valor do eixo para G920 e outros"""
        # G920: -1.0 = pedal solto, +1.0 = pedal pressionado
        # Queremos: 0.0 = pedal solto, 1.0 = pedal pressionado
        normalized = (1.0 - raw_value) / 2.0
        return max(0.0, min(1.0, normalized))

    def _start_simulation(self):
        """Fallback para dados simulados"""
        self.connected = False
        self.running = True
        self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.thread.start()
        return True

    def _simulation_loop(self):
        """Loop de simulação de dados"""
        while self.running:
            t = time.time()
            throttle_base = max(0, 0.5 + 0.4 * math.sin(t * 0.7))
            brake_base = max(0, 0.3 + 0.3 * math.sin(t * 0.4 + math.pi))

            self.throttle = throttle_base + math.sin(t * 2.1) * 0.1
            self.brake = brake_base if brake_base > 0.2 else 0

            if self.brake > 0.3:
                self.throttle *= 0.2

            time.sleep(0.016)

    def stop(self):
        """Para leitura"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

        # Cleanup pygame se foi inicializado
        if self.joysticks:
            import pygame
            for joystick in self.joysticks:
                if joystick.get_init():
                    joystick.quit()
            pygame.joystick.quit()

class GraphCanvas(QWidget):
    """Canvas para desenhar o gráfico histórico - PARTE PRINCIPAL!"""
    def __init__(self):
        super().__init__()
        self.throttle_history = []
        self.brake_history = []
        self.setStyleSheet("background-color: rgba(20, 20, 35, 150); border: 1px solid rgba(100, 200, 255, 100);")

    def update_data(self, throttle_history, brake_history):
        """Atualiza dados do gráfico"""
        self.throttle_history = throttle_history
        self.brake_history = brake_history
        self.update()  # Redesenha

    def paintEvent(self, event):
        """Desenha o gráfico como áreas preenchidas (igual à imagem referência)"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Área de desenho
        rect = self.rect()
        margin = 5
        graph_rect = rect.adjusted(margin, margin, -margin, -margin)

        # Background do gráfico (escuro como na imagem)
        painter.fillRect(graph_rect, QBrush(QColor(40, 40, 40, 200)))

        # Grid horizontal sutil
        painter.setPen(QPen(QColor(80, 80, 80, 60), 1))
        for i in range(1, 4):  # 25%, 50%, 75%
            y = graph_rect.bottom() - (graph_rect.height() * i / 4)
            painter.drawLine(graph_rect.left(), y, graph_rect.right(), y)

        # Desenhar linhas minimalistas se temos dados
        if len(self.throttle_history) > 1 and len(self.brake_history) > 1:
            # Throttle line (verde) - estilo minimalista
            painter.setPen(QPen(QColor(0, 255, 120), 2))
            prev_point = None
            for i, value in enumerate(self.throttle_history):
                x = graph_rect.left() + (i * graph_rect.width() / max(1, len(self.throttle_history) - 1))
                y = graph_rect.bottom() - (value * graph_rect.height())
                point = QPoint(int(x), int(y))

                if prev_point:
                    painter.drawLine(prev_point, point)
                prev_point = point

            # Brake line (vermelho) - estilo minimalista
            painter.setPen(QPen(QColor(255, 50, 80), 2))
            prev_point = None
            for i, value in enumerate(self.brake_history):
                x = graph_rect.left() + (i * graph_rect.width() / max(1, len(self.brake_history) - 1))
                y = graph_rect.bottom() - (value * graph_rect.height())
                point = QPoint(int(x), int(y))

                if prev_point:
                    painter.drawLine(prev_point, point)
                prev_point = point

class TinyPedalOverlay(QWidget):
    """
    Overlay inspirado no TinyPedal
    Usa as mesmas técnicas: Qt/PySide com window flags apropriados
    """
    def __init__(self):
        super().__init__()

        print("TINYPEDAL-INSPIRED OVERLAY")
        print("=" * 60)
        print(f"Usando: {PYSIDE_VERSION}")
        print("Baseado na analise do projeto TinyPedal (que realmente funciona)")

        # Configurar pedais
        self.pedal_reader = RealPedalReader()
        self.pedal_reader.start()

        # Contador para debug
        self.update_count = 0

        # Histórico para gráfico (PRINCIPAL!)
        self.max_history = 150  # ~5 segundos a 30fps
        self.throttle_history = []
        self.brake_history = []

        # Drag functionality
        self.dragging = False
        self.drag_start_position = None

        # Toggle visibility
        self.is_visible = True

        # Setup overlay
        self.setup_overlay_window()
        self.setup_ui()
        self.setup_timer()
        self.setup_hotkeys()

    def setup_overlay_window(self):
        """
        Configura janela overlay usando técnicas do TinyPedal
        ESTA É A PARTE CRÍTICA!
        """
        print("  Configurando janela overlay (técnica TinyPedal)...")

        # 1. Window Flags - TÉCNICA CHAVE DO TINYPEDAL!
        # Combinação que realmente funciona para overlays
        window_flags = (
            Qt.Tool |                    # Evita aparecer na barra de tarefas
            Qt.FramelessWindowHint |     # Remove decorações da janela
            Qt.WindowStaysOnTopHint |    # SEMPRE POR CIMA (Qt faz isso direito!)
            Qt.X11BypassWindowManagerHint  # Bypass window manager (Linux)
        )

        self.setWindowFlags(window_flags)

        # 2. Window Attributes - TÉCNICA DO TINYPEDAL
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # Background translúcido
        self.setAttribute(Qt.WA_NoSystemBackground, True)     # Sem background do sistema
        self.setAttribute(Qt.WA_AlwaysShowToolTips, True)     # Sempre mostra tooltips

        # 3. Tamanho ajustado: altura -35%
        self.resize(400, 195)  # 300 * 0.65 = 195
        self.move(100, 100)

        # 4. Estilo com MENOS opacidade (mais transparente)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 15, 25, 180);
                color: white;
                border: 1px solid rgba(100, 200, 255, 120);
                border-radius: 6px;
            }
            QLabel {
                border: none;
                padding: 2px;
                background-color: transparent;
            }
            QProgressBar {
                border: 1px solid rgba(100, 100, 100, 80);
                border-radius: 3px;
                text-align: center;
                background-color: rgba(40, 40, 60, 100);
            }
            QProgressBar::chunk {
                border-radius: 2px;
            }
        """)

        print("    Janela configurada com técnicas REAIS do TinyPedal")

    def setup_ui(self):
        """Setup interface como TinyPedal widgets"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Título
        title = QLabel("Kenji Overlay")
        title.setFont(QFont("Arial", 6, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: rgba(255, 255, 255, 150); background-color: transparent;")
        layout.addWidget(title)

        # Status
        self.status_label = QLabel("Qt Overlay - Técnicas TinyPedal")
        self.status_label.setFont(QFont("Arial", 6))
        self.status_label.setStyleSheet("color: #64C8FF;")
        layout.addWidget(self.status_label)

        # Layout principal: tudo em linha horizontal
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)

        # 1. Gráfico (lado esquerdo - largura +50%)
        self.graph_canvas = GraphCanvas()
        self.graph_canvas.setMinimumHeight(65)  # Reduzido para caber na altura menor
        self.graph_canvas.setMinimumWidth(300)  # 200 * 1.5 = 300
        main_layout.addWidget(self.graph_canvas)

        # 2. Throttle vertical (meio)
        throttle_container = QVBoxLayout()
        throttle_container.setSpacing(2)

        throttle_label = QLabel("THR")
        throttle_label.setAlignment(Qt.AlignCenter)
        throttle_label.setFont(QFont("Arial", 8))
        throttle_container.addWidget(throttle_label)

        self.throttle_bar = QProgressBar()
        self.throttle_bar.setMaximum(100)
        self.throttle_bar.setOrientation(Qt.Vertical)
        self.throttle_bar.setMinimumHeight(52)  # 80 * 0.65 = 52
        self.throttle_bar.setMaximumWidth(20)
        self.throttle_bar.setStyleSheet("QProgressBar::chunk { background-color: #00FF78; }")
        throttle_container.addWidget(self.throttle_bar)

        self.throttle_label = QLabel("0%")
        self.throttle_label.setAlignment(Qt.AlignCenter)
        self.throttle_label.setFont(QFont("Arial", 7))
        throttle_container.addWidget(self.throttle_label)

        # Adicionar throttle ao layout principal
        main_layout.addLayout(throttle_container)

        # 3. Brake vertical (direita)
        brake_container = QVBoxLayout()
        brake_container.setSpacing(2)

        brake_label = QLabel("BRK")
        brake_label.setAlignment(Qt.AlignCenter)
        brake_label.setFont(QFont("Arial", 8))
        brake_container.addWidget(brake_label)

        self.brake_bar = QProgressBar()
        self.brake_bar.setMaximum(100)
        self.brake_bar.setOrientation(Qt.Vertical)
        self.brake_bar.setMinimumHeight(52)  # 80 * 0.65 = 52
        self.brake_bar.setMaximumWidth(20)
        self.brake_bar.setStyleSheet("QProgressBar::chunk { background-color: #FF3250; }")
        brake_container.addWidget(self.brake_bar)

        self.brake_label = QLabel("0%")
        self.brake_label.setAlignment(Qt.AlignCenter)
        self.brake_label.setFont(QFont("Arial", 7))
        brake_container.addWidget(self.brake_label)

        # Adicionar brake ao layout principal
        main_layout.addLayout(brake_container)

        layout.addLayout(main_layout)


        # Instruções
        instructions = QLabel("ARRASTE para mover | V = Toggle | ESC = Fechar")
        instructions.setFont(QFont("Arial", 8))
        instructions.setStyleSheet("color: #FFC800;")
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)

    def setup_timer(self):
        """Timer de atualização (como TinyPedal)"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(33)  # ~30fps

    def setup_hotkeys(self):
        """Configurar detecção de F12 para toggle"""
        # Usar apenas detecção global (mais simples e funciona melhor)
        self.hotkey_timer = QTimer()
        self.hotkey_timer.timeout.connect(self.check_global_hotkeys)
        self.hotkey_timer.start(100)  # Verificar a cada 100ms
        self._f12_pressed = False

        print("    V = Toggle overlay visibility")
        print("    Ctrl+U = Verificar atualizações")

    def check_global_hotkeys(self):
        """Verifica teclas globais mesmo quando overlay não tem foco"""
        try:
            import win32api
            import win32con

            # Verificar se V foi pressionada (0x56 é o código da tecla V)
            if win32api.GetAsyncKeyState(0x56) & 0x8000:
                if not self._f12_pressed:
                    self._f12_pressed = True
                    self.toggle_visibility()
            else:
                self._f12_pressed = False

        except ImportError:
            # Fallback: usar pygame para detectar V (menos eficiente)
            try:
                import pygame
                keys = pygame.key.get_pressed()
                if keys[pygame.K_v]:
                    if not self._f12_pressed:
                        self._f12_pressed = True
                        self.toggle_visibility()
                else:
                    self._f12_pressed = False
            except:
                # Se nada funcionar, apenas reportar
                pass

    def toggle_visibility(self):
        """Alterna visibilidade do overlay"""
        self.is_visible = not self.is_visible

        if self.is_visible:
            self.show()
            print("Overlay VISÍVEL - V para esconder")
        else:
            self.hide()
            print("Overlay ESCONDIDO - V para mostrar")

        # Feedback visual rápido no console
        status = "VISÍVEL" if self.is_visible else "ESCONDIDO"
        print(f"Toggle: Overlay {status}")

    def update_data(self):
        """Atualiza dados do overlay"""
        self.update_count += 1

        # Pega dados dos pedais
        throttle = max(0, min(1, self.pedal_reader.throttle))
        brake = max(0, min(1, self.pedal_reader.brake))

        # Adicionar ao histórico (PRINCIPAL!)
        self.throttle_history.append(throttle)
        self.brake_history.append(brake)

        # Limitar histórico
        if len(self.throttle_history) > self.max_history:
            self.throttle_history.pop(0)
        if len(self.brake_history) > self.max_history:
            self.brake_history.pop(0)

        # Atualizar gráfico (PRINCIPAL!)
        self.graph_canvas.update_data(self.throttle_history, self.brake_history)

        # Atualiza UI
        self.throttle_bar.setValue(int(throttle * 100))
        self.throttle_label.setText(f"{int(throttle * 100)}%")

        self.brake_bar.setValue(int(brake * 100))
        self.brake_label.setText(f"{int(brake * 100)}%")

        # Status atualizado
        if self.pedal_reader.connected:
            status_text = "Pedais Conectados"
            status_color = "#00FF78"
        else:
            status_text = "Dados simulados (sem pedais)"
            status_color = "#FFC800"

        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"color: {status_color};")


    def mousePressEvent(self, event):
        """Inicia drag do overlay"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_position = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        """Arrasta overlay pela tela"""
        if self.dragging and (event.buttons() & Qt.LeftButton):
            new_position = event.globalPos() - self.drag_start_position
            self.move(new_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Termina drag do overlay"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()

    def keyPressEvent(self, event):
        """Handle key events"""
        if event.key() == Qt.Key_Escape:
            print("Fechando overlay...")
            self.close()
        elif event.key() == Qt.Key_U and event.modifiers() == Qt.ControlModifier:
            print("🔍 Verificando atualizações...")
            self.check_for_updates()

    def check_for_updates(self):
        """Verifica e mostra dialog de atualização"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
            from src.updater import show_update_dialog

            # Executar em thread separada para não bloquear UI
            import threading
            threading.Thread(target=show_update_dialog, daemon=True).start()
        except Exception as e:
            print(f"❌ Erro ao verificar atualizações: {e}")

    def closeEvent(self, event):
        """Cleanup ao fechar"""
        print("Limpando overlay...")
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        if hasattr(self, 'hotkey_timer'):
            self.hotkey_timer.stop()
        self.pedal_reader.stop()
        event.accept()

def main():
    print("INICIANDO TINYPEDAL-INSPIRED OVERLAY")
    print("Baseado na análise de um projeto que REALMENTE funciona")
    print()

    # Criar aplicação Qt
    app = QApplication(sys.argv)

    # Configurações da aplicação (como TinyPedal)
    app.setApplicationName("TinyPedal-Inspired Overlay")
    app.setQuitOnLastWindowClosed(True)

    # Criar e mostrar overlay
    try:
        overlay = TinyPedalOverlay()
        overlay.show()

        print()
        print("OVERLAY ATIVO COM TÉCNICAS DO TINYPEDAL!")
        print("=" * 60)
        print("TÉCNICAS IMPLEMENTADAS:")
        print("  - Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint")
        print("  - Qt.WA_TranslucentBackground")
        print("  - Estilo similar ao TinyPedal")
        print("  - Timer de atualização (30fps)")
        print("  - Layout modular de widgets")
        print("  - V = Toggle visibility")
        print()
        print("TESTE AGORA:")
        print("- Clique em VS Code, browser, qualquer aplicação")
        print("- Overlay deve permanecer SEMPRE VISÍVEL")
        print("- Baseado em projeto que comprovadamente funciona")
        print("=" * 60)

        # Executar aplicação
        sys.exit(app.exec())

    except Exception as e:
        print(f"Erro crítico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()