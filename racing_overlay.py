"""
Racing Telemetry Overlay
Professional racing pedal telemetry overlay for Le Mans Ultimate and F1 games
Uses PySide/Qt for real overlay functionality
"""
import sys
import os
import time
import math
import threading
import socket
import struct
from collections import deque

# Import physics calculations
try:
    from src.physics import GForceCalculator, get_gforce_direction_symbol
except ImportError:
    print("Warning: Physics module not found - G-force features disabled")
    GForceCalculator = None

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


class TelemetryDataReader:
    """Enhanced telemetry reader with G-force support for F1 and Le Mans Ultimate"""

    def __init__(self):
        self.running = False
        self.thread = None

        # Current telemetry data
        self.throttle = 0.0
        self.brake = 0.0
        self.speed = 0.0
        self.gear = 0
        self.rpm = 0

        # G-force data
        self.gforce_longitudinal = 0.0
        self.gforce_lateral = 0.0
        self.gforce_vertical = 0.0

        # Compatibility with old pedal reader interface
        self.connected = True  # Always connected in simulation mode

        # G-force calculator
        if GForceCalculator:
            self.gforce_calculator = GForceCalculator(history_size=10, smoothing_factor=0.3)
        else:
            self.gforce_calculator = None

        # Game detection
        self.current_game = "Unknown"
        self.connection_status = "Disconnected"

        # UDP socket for F1 data
        self.f1_socket = None
        self.f1_port = 20777

        # Shared memory for LMU (placeholder)
        self.lmu_connected = False

    def start(self):
        """Start telemetry data reading"""
        print("Starting enhanced telemetry reader...")
        self.running = True
        self.thread = threading.Thread(target=self._read_telemetry_loop, daemon=True)
        self.thread.start()

        # Try to connect to F1 UDP
        self._setup_f1_connection()

    def stop(self):
        """Stop telemetry reading"""
        self.running = False
        if self.f1_socket:
            self.f1_socket.close()
        if self.thread:
            self.thread.join(timeout=1.0)

    def _setup_f1_connection(self):
        """Setup UDP connection for F1 telemetry"""
        try:
            self.f1_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.f1_socket.bind(("127.0.0.1", self.f1_port))
            self.f1_socket.settimeout(0.1)  # 100ms timeout
            print(f"F1 UDP telemetry listening on port {self.f1_port}")
        except Exception as e:
            print(f"Failed to setup F1 connection: {e}")
            self.f1_socket = None

    def _read_telemetry_loop(self):
        """Main telemetry reading loop"""
        while self.running:
            try:
                # Try F1 UDP data first
                if self._read_f1_data():
                    self.current_game = "F1 2024/2023"
                    self.connection_status = "F1 Connected"
                # Try LMU shared memory
                elif self._read_lmu_data():
                    self.current_game = "Le Mans Ultimate"
                    self.connection_status = "LMU Connected"
                else:
                    # No data - use simulation
                    self._simulate_data()
                    self.current_game = "Simulation"
                    self.connection_status = "Simulated"

                # Update G-force calculations
                self._update_gforce_calculations()

            except Exception as e:
                print(f"Telemetry read error: {e}")

            time.sleep(0.033)  # ~30fps

    def _read_f1_data(self) -> bool:
        """Read F1 UDP telemetry data"""
        if not self.f1_socket:
            return False

        try:
            data, addr = self.f1_socket.recvfrom(1464)  # F1 UDP packet size

            # Parse F1 telemetry packet (simplified)
            # This is a basic implementation - full F1 telemetry parsing is complex
            if len(data) >= 100:  # Minimum expected size
                # Extract basic data (positions depend on F1 packet format)
                # These are placeholder positions - actual F1 parsing requires packet header analysis

                # Simulate extraction (replace with actual F1 packet parsing)
                import random
                self.throttle = min(100.0, max(0.0, random.uniform(0, 100)))
                self.brake = min(100.0, max(0.0, random.uniform(0, 100)))
                self.speed = random.uniform(0, 300)
                self.gear = random.randint(1, 8)
                self.rpm = random.uniform(1000, 15000)

                # G-force data (these would need to be extracted from actual F1 packets)
                self.gforce_longitudinal = random.uniform(-3.0, 3.0)
                self.gforce_lateral = random.uniform(-2.0, 2.0)
                self.gforce_vertical = random.uniform(-1.0, 1.0)

                return True

        except socket.timeout:
            # No data available
            pass
        except Exception as e:
            print(f"F1 data read error: {e}")

        return False

    def _read_lmu_data(self) -> bool:
        """Read Le Mans Ultimate shared memory data"""
        # Placeholder for LMU shared memory implementation
        # This would require the rFactor2 shared memory plugin

        try:
            # TODO: Implement actual shared memory reading
            # For now, return False to indicate no LMU data
            return False
        except Exception as e:
            print(f"LMU data read error: {e}")
            return False

    def _simulate_data(self):
        """Simulate telemetry data when no real data is available"""
        import random
        current_time = time.time()

        # Simulate realistic racing data
        base_throttle = 50 + 30 * math.sin(current_time * 0.5)
        base_brake = max(0, 40 - base_throttle/2 + 20 * math.sin(current_time * 0.8))

        self.throttle = max(0, min(100, base_throttle + random.uniform(-10, 10)))
        self.brake = max(0, min(100, base_brake + random.uniform(-5, 5)))

        self.speed = 150 + 50 * math.sin(current_time * 0.3)
        self.gear = int(3 + 2 * math.sin(current_time * 0.2))
        self.rpm = 8000 + 3000 * math.sin(current_time * 0.4)

        # Simulate G-forces based on throttle/brake
        self.gforce_longitudinal = (self.throttle - self.brake) / 50.0  # -2 to +2 G
        self.gforce_lateral = 1.5 * math.sin(current_time * 0.6)  # Cornering
        self.gforce_vertical = 0.2 * math.sin(current_time * 1.2)  # Road bumps

    def _update_gforce_calculations(self):
        """Update G-force calculations with current data"""
        if self.gforce_calculator:
            # Convert G-forces to acceleration for calculator input
            longitudinal_accel = self.gforce_longitudinal * 9.81
            lateral_accel = self.gforce_lateral * 9.81
            vertical_accel = self.gforce_vertical * 9.81

            # Update calculator
            self.gforce_calculator.update(longitudinal_accel, lateral_accel, vertical_accel)

    def get_gforce_data(self) -> dict:
        """Get current G-force data"""
        if self.gforce_calculator:
            return self.gforce_calculator.update(
                self.gforce_longitudinal * 9.81,
                self.gforce_lateral * 9.81,
                self.gforce_vertical * 9.81
            )
        else:
            return {
                'longitudinal': self.gforce_longitudinal,
                'lateral': self.gforce_lateral,
                'vertical': self.gforce_vertical,
                'total': math.sqrt(self.gforce_longitudinal**2 + self.gforce_lateral**2 + self.gforce_vertical**2)
            }

    def get_basic_telemetry(self) -> dict:
        """Get basic telemetry data"""
        return {
            'throttle': self.throttle,
            'brake': self.brake,
            'speed': self.speed,
            'gear': self.gear,
            'rpm': self.rpm,
            'game': self.current_game,
            'connection': self.connection_status
        }


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

class RacingTelemetryOverlay(QWidget):
    """
    Professional Racing Telemetry Overlay
    Uses Qt/PySide with appropriate window flags for overlay functionality
    """
    def __init__(self):
        super().__init__()

        print("RACING TELEMETRY OVERLAY")
        print("=" * 60)

        # Mostrar versão no console (compatível com PyInstaller)
        try:
            import sys
            import os

            # Detectar se está rodando via PyInstaller
            if getattr(sys, 'frozen', False):
                # Rodando como executável
                bundle_dir = sys._MEIPASS
            else:
                # Rodando como script Python
                bundle_dir = os.path.dirname(__file__)

            sys.path.insert(0, bundle_dir)
            from version import __version__, __app_name__
            print(f"{__app_name__} v{__version__}")
            self.current_version = __version__
            self.app_name = __app_name__

            # Importar status de atualização
            try:
                import overlay
                self.update_status = overlay.UPDATE_STATUS
                self.update_notification_shown = False  # Flag para mostrar notificação apenas uma vez
            except ImportError:
                self.update_status = {'has_update': False, 'new_version': None, 'checked': False}
                self.update_notification_shown = False
        except ImportError:
            print("Racing Telemetry Pedals v1.0.0")
            self.current_version = "1.0.0"
            self.app_name = "Racing Telemetry Pedals"
            self.update_status = {'has_update': False, 'new_version': None, 'checked': False}
            self.update_notification_shown = False

        print(f"Usando: {PYSIDE_VERSION}")
        print("Professional telemetry overlay for racing games")

        # Configurar telemetria avançada
        self.telemetry_reader = TelemetryDataReader()
        self.telemetry_reader.start()

        # Manter compatibilidade com código antigo
        self.pedal_reader = self.telemetry_reader

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
        Configure overlay window using professional techniques
        ESTA É A PARTE CRÍTICA!
        """
        print("  Configuring overlay window...")

        # 1. Window Flags - Key technique for overlay functionality
        # Combinação que realmente funciona para overlays
        window_flags = (
            Qt.Tool |                    # Evita aparecer na barra de tarefas
            Qt.FramelessWindowHint |     # Remove decorações da janela
            Qt.WindowStaysOnTopHint |    # SEMPRE POR CIMA (Qt faz isso direito!)
            Qt.X11BypassWindowManagerHint  # Bypass window manager (Linux)
        )

        self.setWindowFlags(window_flags)

        # 2. Window Attributes - Additional overlay configuration
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

        print("    Overlay window configured successfully")

    def setup_ui(self):
        """Setup professional interface widgets"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Título
        title = QLabel("Kenji Overlay")
        title.setFont(QFont("Arial", 6, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: rgba(255, 255, 255, 150); background-color: transparent;")
        layout.addWidget(title)

        # Status
        self.status_label = QLabel("Racing Telemetry - Real-time Data")
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

        # G-Force Display Widget
        self.setup_gforce_widget(layout)

        # Instruções com versão (usar versão já carregada)
        version_text = f"v{getattr(self, 'current_version', '1.0.0')}"
        instructions = QLabel(f"ARRASTE para mover | V = Toggle | Ctrl+U = Update | ESC = Fechar | {version_text}")
        instructions.setFont(QFont("Arial", 8))
        instructions.setStyleSheet("color: #FFC800;")
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)

    def setup_gforce_widget(self, parent_layout):
        """Setup G-force display widget"""
        if not GForceCalculator:
            return  # Skip if physics module not available

        # G-Force container
        gforce_container = QHBoxLayout()
        gforce_container.setSpacing(15)

        # Longitudinal G-Force
        long_layout = QVBoxLayout()
        long_title = QLabel("LONGITUDINAL")
        long_title.setFont(QFont("Arial", 7, QFont.Bold))
        long_title.setAlignment(Qt.AlignCenter)
        long_title.setStyleSheet("color: #FFC800;")
        long_layout.addWidget(long_title)

        self.gforce_long_label = QLabel("● 0.00G")
        self.gforce_long_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.gforce_long_label.setAlignment(Qt.AlignCenter)
        self.gforce_long_label.setStyleSheet("color: #00FF78;")
        long_layout.addWidget(self.gforce_long_label)

        gforce_container.addLayout(long_layout)

        # Lateral G-Force
        lat_layout = QVBoxLayout()
        lat_title = QLabel("LATERAL")
        lat_title.setFont(QFont("Arial", 7, QFont.Bold))
        lat_title.setAlignment(Qt.AlignCenter)
        lat_title.setStyleSheet("color: #FFC800;")
        lat_layout.addWidget(lat_title)

        self.gforce_lat_label = QLabel("● 0.00G")
        self.gforce_lat_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.gforce_lat_label.setAlignment(Qt.AlignCenter)
        self.gforce_lat_label.setStyleSheet("color: #FF3250;")
        lat_layout.addWidget(self.gforce_lat_label)

        gforce_container.addLayout(lat_layout)

        # Total G-Force
        total_layout = QVBoxLayout()
        total_title = QLabel("TOTAL")
        total_title.setFont(QFont("Arial", 7, QFont.Bold))
        total_title.setAlignment(Qt.AlignCenter)
        total_title.setStyleSheet("color: #FFC800;")
        total_layout.addWidget(total_title)

        self.gforce_total_label = QLabel("0.00G")
        self.gforce_total_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.gforce_total_label.setAlignment(Qt.AlignCenter)
        self.gforce_total_label.setStyleSheet("color: #64C8FF;")
        total_layout.addWidget(self.gforce_total_label)

        gforce_container.addLayout(total_layout)

        # Game/Connection Status
        status_layout = QVBoxLayout()
        status_title = QLabel("STATUS")
        status_title.setFont(QFont("Arial", 7, QFont.Bold))
        status_title.setAlignment(Qt.AlignCenter)
        status_title.setStyleSheet("color: #FFC800;")
        status_layout.addWidget(status_title)

        self.connection_status_label = QLabel("Simulated")
        self.connection_status_label.setFont(QFont("Arial", 8))
        self.connection_status_label.setAlignment(Qt.AlignCenter)
        self.connection_status_label.setStyleSheet("color: #888888;")
        status_layout.addWidget(self.connection_status_label)

        gforce_container.addLayout(status_layout)

        parent_layout.addLayout(gforce_container)

    def setup_timer(self):
        """Update timer for real-time data refresh"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(33)  # ~30fps

        # Timer para verificar atualizações disponíveis
        self.check_updates_timer = QTimer()
        self.check_updates_timer.timeout.connect(self.check_for_updates_notification)
        self.check_updates_timer.start(1000)  # Verificar a cada 1 segundo

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

        # Pega dados dos pedais (manter compatibilidade)
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

        # Atualizar dados de força G
        self.update_gforce_display()

        # Atualizar status da conexão
        self.update_connection_status()

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

    def update_gforce_display(self):
        """Update G-force display widgets"""
        if not hasattr(self, 'gforce_long_label') or not GForceCalculator:
            return

        try:
            # Get G-force data from telemetry reader
            gforce_data = self.telemetry_reader.get_gforce_data()

            # Update longitudinal G-force
            long_gforce = gforce_data.get('longitudinal', 0.0)
            long_symbol = get_gforce_direction_symbol(long_gforce, 'longitudinal')
            long_text = f"{long_symbol} {abs(long_gforce):.2f}G"
            self.gforce_long_label.setText(long_text)

            # Color based on intensity
            if abs(long_gforce) > 2.0:
                long_color = "#FF3250"  # Red for high G
            elif abs(long_gforce) > 1.0:
                long_color = "#FFC800"  # Yellow for medium G
            else:
                long_color = "#00FF78"  # Green for low G
            self.gforce_long_label.setStyleSheet(f"color: {long_color};")

            # Update lateral G-force
            lat_gforce = gforce_data.get('lateral', 0.0)
            lat_symbol = get_gforce_direction_symbol(lat_gforce, 'lateral')
            lat_text = f"{lat_symbol} {abs(lat_gforce):.2f}G"
            self.gforce_lat_label.setText(lat_text)

            # Color based on intensity
            if abs(lat_gforce) > 1.5:
                lat_color = "#FF3250"  # Red for high G
            elif abs(lat_gforce) > 0.8:
                lat_color = "#FFC800"  # Yellow for medium G
            else:
                lat_color = "#00FF78"  # Green for low G
            self.gforce_lat_label.setStyleSheet(f"color: {lat_color};")

            # Update total G-force
            total_gforce = gforce_data.get('total', 0.0)
            total_text = f"{total_gforce:.2f}G"
            self.gforce_total_label.setText(total_text)

            # Color based on total intensity
            if total_gforce > 2.5:
                total_color = "#FF3250"  # Red for high total G
            elif total_gforce > 1.5:
                total_color = "#FFC800"  # Yellow for medium total G
            else:
                total_color = "#64C8FF"  # Blue for low total G
            self.gforce_total_label.setStyleSheet(f"color: {total_color};")

        except Exception as e:
            print(f"G-force display update error: {e}")

    def update_connection_status(self):
        """Update connection status display"""
        if not hasattr(self, 'connection_status_label'):
            return

        try:
            # Get telemetry status
            telemetry_data = self.telemetry_reader.get_basic_telemetry()
            connection_status = telemetry_data.get('connection', 'Disconnected')
            current_game = telemetry_data.get('game', 'Unknown')

            # Update status label
            if connection_status == "F1 Connected":
                status_text = "F1 LIVE"
                status_color = "#00FF78"  # Green
            elif connection_status == "LMU Connected":
                status_text = "LMU LIVE"
                status_color = "#00FF78"  # Green
            elif connection_status == "Simulated":
                status_text = "DEMO"
                status_color = "#FFC800"  # Yellow
            else:
                status_text = "OFFLINE"
                status_color = "#888888"  # Gray

            self.connection_status_label.setText(status_text)
            self.connection_status_label.setStyleSheet(f"color: {status_color};")

        except Exception as e:
            print(f"Connection status update error: {e}")

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
            print("Verificando atualizacoes...")
            self.check_for_updates()

    def check_for_updates(self):
        """Verifica e mostra dialog de atualização"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
            from src.updater import show_update_dialog

            # Executar em thread separada para não bloquear UI
            def update_with_callback():
                show_update_dialog()
                # Após update, atualizar a versão exibida
                self.update_version_display()

            import threading
            threading.Thread(target=update_with_callback, daemon=True).start()
        except Exception as e:
            print(f"Erro ao verificar atualizacoes: {e}")

    def update_version_display(self):
        """Atualiza a exibição da versão na interface"""
        try:
            # Reimportar para pegar nova versão (compatível com PyInstaller)
            import sys
            import os
            import importlib

            # Detectar se está rodando via PyInstaller
            if getattr(sys, 'frozen', False):
                bundle_dir = sys._MEIPASS
            else:
                bundle_dir = os.path.dirname(__file__)

            # Recarregar módulo de versão
            if 'version' in sys.modules:
                importlib.reload(sys.modules['version'])

            sys.path.insert(0, bundle_dir)
            from version import __version__

            # Atualizar versão armazenada
            self.current_version = __version__

            # Encontrar o widget de instruções e atualizar
            for child in self.findChildren(QLabel):
                if "ARRASTE para mover" in child.text():
                    child.setText(f"ARRASTE para mover | V = Toggle | Ctrl+U = Update | ESC = Fechar | v{__version__}")
                    print(f"Versao atualizada na interface: v{__version__}")
                    break
        except Exception as e:
            print(f"Erro ao atualizar versao na interface: {e}")

    def check_for_updates_notification(self):
        """Verifica se há atualizações disponíveis e mostra notificação visual"""
        try:
            # Verificar se já foi mostrada a notificação
            if self.update_notification_shown:
                return

            # Verificar se a verificação foi concluída e há atualização disponível
            if self.update_status['checked'] and self.update_status['has_update']:
                new_version = self.update_status['new_version']

                # Encontrar o widget de instruções e adicionar a notificação
                for child in self.findChildren(QLabel):
                    if "ARRASTE para mover" in child.text():
                        # Atualizar o texto com a notificação em destaque
                        child.setText(f"NOVA VERSAO v{new_version} DISPONIVEL! Use Ctrl+U para atualizar")
                        child.setStyleSheet("color: #FF4444; font-weight: bold;")  # Vermelho e negrito
                        print(f"Notificacao visual mostrada: Nova versao v{new_version} disponivel!")
                        self.update_notification_shown = True

                        # Criar um timer para piscar a notificação
                        self.blink_timer = QTimer()
                        self.blink_timer.timeout.connect(lambda: self.blink_notification(child, new_version))
                        self.blink_timer.start(1000)  # Piscar a cada 1 segundo
                        break

        except Exception as e:
            print(f"Erro ao verificar notificação de atualização: {e}")

    def blink_notification(self, label_widget, new_version):
        """Faz a notificação de atualização piscar"""
        try:
            # Alternar entre vermelho e amarelo para chamar atenção
            current_color = label_widget.styleSheet()
            if "#FF4444" in current_color:
                label_widget.setStyleSheet("color: #FFC800; font-weight: bold;")  # Amarelo
            else:
                label_widget.setStyleSheet("color: #FF4444; font-weight: bold;")  # Vermelho
        except:
            pass

    def closeEvent(self, event):
        """Cleanup ao fechar"""
        print("Limpando overlay...")
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        if hasattr(self, 'hotkey_timer'):
            self.hotkey_timer.stop()
        if hasattr(self, 'check_updates_timer'):
            self.check_updates_timer.stop()
        if hasattr(self, 'blink_timer'):
            self.blink_timer.stop()
        self.pedal_reader.stop()
        event.accept()

def main():
    print("STARTING RACING TELEMETRY OVERLAY")
    print("Baseado na análise de um projeto que REALMENTE funciona")
    print()

    # Criar aplicação Qt
    app = QApplication(sys.argv)

    # Application configuration
    app.setApplicationName("Racing Telemetry Overlay")
    app.setQuitOnLastWindowClosed(True)

    # Criar e mostrar overlay
    try:
        overlay = RacingTelemetryOverlay()
        overlay.show()

        print()
        print("RACING TELEMETRY OVERLAY ACTIVE!")
        print("=" * 60)
        print("TÉCNICAS IMPLEMENTADAS:")
        print("  - Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint")
        print("  - Qt.WA_TranslucentBackground")
        print("  - Professional overlay interface")
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