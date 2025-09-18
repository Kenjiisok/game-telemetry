"""
Telemetria rF2/LMU CORRIGIDA
Utiliza a biblioteca oficial pyRfactor2SharedMemory

Sistema otimizado para leitura precisa de telemetria.
"""

import time
import threading
from typing import Optional, Tuple

# Importar biblioteca oficial
try:
    from pyRfactor2SharedMemory import sharedMemoryAPI
    RF2_AVAILABLE = True
except ImportError:
    RF2_AVAILABLE = False


class RF2TelemetryManager:
    """
    Gerenciador de telemetria rF2/LMU CORRIGIDO
    Utiliza biblioteca oficial pyRfactor2SharedMemory
    """

    def __init__(self):
        self.api = None
        self.running = False
        self.connected = False
        self.thread = None

        # Dados atuais de força G
        self.gforce_lateral = 0.0
        self.gforce_longitudinal = 0.0
        self.gforce_vertical = 0.0

        # Dados básicos de telemetria
        self.speed = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        self.gear = 0
        self.rpm = 0.0

        # Estado da conexão
        self.last_valid_read = 0.0
        self.connection_failures = 0
        self.max_failures = 10

        # Configuração de aceleração gravitacional
        self.g_accel = 9.80665  # Constante gravitacional padrão

    def start(self) -> bool:
        """Inicia leitura de telemetria"""
        if not RF2_AVAILABLE:
            return False

        try:

            # Inicializar API oficial
            self.api = sharedMemoryAPI.SimInfoAPI()

            # Verificar versão do shared memory
            if not self.api.sharedMemoryVerified:
                return False


            # Iniciar thread de leitura
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()

            return True

        except Exception as e:
            return False

    def stop(self):
        """Para leitura de telemetria"""
        self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)


    def _read_loop(self):
        """Loop principal de leitura de telemetria"""

        while self.running:
            try:
                # Verificar se RF2 está rodando e shared memory disponível
                if not self.api.isSharedMemoryAvailable():
                    self._reset_data()
                    time.sleep(0.5)
                    continue

                # Verificar se o jogo está ativo
                if not self._is_game_active():
                    self._reset_data()
                    time.sleep(0.1)
                    continue

                # Ler telemetria do player
                if self._read_player_telemetry():
                    self.connected = True
                    self.connection_failures = 0
                    self.last_valid_read = time.time()
                else:
                    self._handle_connection_failure()

            except Exception as e:
                self._handle_connection_failure()

            time.sleep(0.033)  # ~30fps

    def _is_game_active(self) -> bool:
        """Verifica se o jogo está ativo"""
        try:
            # Usar métodos da API
            if not self.api.isOnTrack():
                return False

            # Verificar se há telemetria válida
            if self.api.Rf2Tele.mNumVehicles <= 0:
                return False

            return True

        except Exception:
            return False

    def _read_player_telemetry(self) -> bool:
        """Lê telemetria do player (IMPLEMENTAÇÃO CORRETA)"""
        try:
            # Usar método da API para obter telemetria do player
            vehicle_tele = self.api.playersVehicleTelemetry()
            vehicle_scor = self.api.playersVehicleScoring()

            # FORÇA G - IMPLEMENTAÇÃO CORRETA
            # Ler aceleração diretamente do mLocalAccel (já vem em m/s²)
            accel_x = vehicle_tele.mLocalAccel.x  # Lateral
            accel_y = vehicle_tele.mLocalAccel.y  # Vertical
            accel_z = vehicle_tele.mLocalAccel.z  # Longitudinal

            # Validar valores (função rmnan)
            accel_x = self._rmnan(accel_x)
            accel_y = self._rmnan(accel_y)
            accel_z = self._rmnan(accel_z)

            # Converter para G-force
            self.gforce_lateral = accel_x / self.g_accel      # X = lateral
            self.gforce_longitudinal = accel_z / self.g_accel  # Z = longitudinal
            self.gforce_vertical = accel_y / self.g_accel     # Y = vertical

            # Ler outros dados básicos
            self.speed = max(0, self._rmnan(vehicle_tele.mLocalVel.z) * 3.6)  # Z velocity para km/h
            self.throttle = max(0, min(100, self._rmnan(vehicle_tele.mUnfilteredThrottle) * 100))
            self.brake = max(0, min(100, self._rmnan(vehicle_tele.mUnfilteredBrake) * 100))
            self.gear = vehicle_tele.mGear
            self.rpm = max(0, self._rmnan(vehicle_tele.mEngineRPM))

            # G-force data processed
            return True

        except Exception as e:
            return False

    def _find_player_index(self) -> int:
        """Encontra índice do player"""
        try:
            for i in range(self.api.Rf2Scor.mNumVehicles):
                if self.api.Rf2Scor.mVehicles[i].mIsPlayer:
                    return i
            return -1
        except Exception:
            return -1

    def _rmnan(self, value: float) -> float:
        """Remove NaN/Inf (função rmnan)"""
        import math
        if math.isnan(value) or math.isinf(value):
            return 0.0
        return value

    def _reset_data(self):
        """Reset dados quando jogo não está ativo"""
        self.gforce_lateral = 0.0
        self.gforce_longitudinal = 0.0
        self.gforce_vertical = 0.0
        self.speed = 0.0
        self.connected = False

    def _handle_connection_failure(self):
        """Gerencia falhas de conexão"""
        self.connection_failures += 1
        self.connected = False

        if self.connection_failures >= self.max_failures:
            self._reset_data()
            time.sleep(0.5)  # Delay maior em caso de múltiplas falhas

    def get_gforce_data(self) -> dict:
        """Retorna dados de força G (compatível com interface existente)"""
        import math

        total_gforce = math.sqrt(
            self.gforce_longitudinal**2 +
            self.gforce_lateral**2 +
            self.gforce_vertical**2
        )

        return {
            'lateral': self.gforce_lateral,
            'longitudinal': self.gforce_longitudinal,
            'vertical': self.gforce_vertical,
            'total': total_gforce
        }

    def get_basic_telemetry(self) -> dict:
        """Retorna dados básicos de telemetria (compatível com interface existente)"""
        return {
            'throttle': self.throttle,
            'brake': self.brake,
            'speed': self.speed,
            'gear': self.gear,
            'rpm': self.rpm,
            'game': 'Le Mans Ultimate' if self.connected else 'Disconnected',
            'connection': 'LMU Connected' if self.connected else 'Offline'
        }

    def is_data_valid(self) -> bool:
        """Verifica se dados são válidos"""
        return (self.connected and
                time.time() - self.last_valid_read < 5.0)


# Função de teste para verificar funcionamento
def test_rf2_telemetry():
    """Testa o sistema de telemetria corrigido"""

    telemetry = RF2TelemetryManager()

    if not telemetry.start():
        return False


    try:
        for i in range(30):
            gforce_data = telemetry.get_gforce_data()
            basic_data = telemetry.get_basic_telemetry()

            print(f"Segundo {i+1:2d}: "
                  f"Lat={gforce_data['lateral']:+.3f}G "
                  f"Long={gforce_data['longitudinal']:+.3f}G "
                  f"Total={gforce_data['total']:.3f}G "
                  f"Speed={basic_data['speed']:.0f}km/h "
                  f"Estado={basic_data['connection']}")

            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n[STOP] Teste interrompido pelo usuário")

    finally:
        telemetry.stop()

    return True


if __name__ == "__main__":
    test_rf2_telemetry()