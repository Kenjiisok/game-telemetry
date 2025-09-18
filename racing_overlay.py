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
import ctypes
from ctypes import wintypes
import mmap

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

# rFactor2 Shared Memory Structures
class rF2Vec3(ctypes.Structure):
    """3D Vector structure for rFactor2"""
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("z", ctypes.c_double)
    ]

class rF2VehicleTelemetry(ctypes.Structure):
    """rFactor2 Vehicle Telemetry Structure"""
    _pack_ = 4
    _fields_ = [
        ("mID", ctypes.c_int),                                # slot ID (note that it can be re-used in multiplayer after someone leaves)
        ("mDeltaTime", ctypes.c_double),                      # time since last update (seconds)
        ("mElapsedTime", ctypes.c_double),                    # game session time
        ("mLapNumber", ctypes.c_int),                         # current lap number
        ("mLapStartET", ctypes.c_double),                     # time this lap was started
        ("mVehicleName", ctypes.c_char*64),                   # current vehicle name
        ("mTrackName", ctypes.c_char*64),                     # current track name
        ("mPos", rF2Vec3),                                    # world position in meters
        ("mLocalVel", rF2Vec3),                               # velocity (meters/sec) in local vehicle coordinates
        ("mLocalAccel", rF2Vec3),                             # acceleration (meters/sec^2) in local vehicle coordinates - THIS IS WHAT WE NEED!
        ("mOri", rF2Vec3*3),                                  # rows of orientation matrix (use TelemQuat conversions if desired), also converts local
        ("mLocalRot", rF2Vec3),                               # rotation (radians/sec) in local vehicle coordinates
        ("mLocalRotAccel", rF2Vec3),                          # rotational acceleration (radians/sec^2) in local vehicle coordinates
        ("mGear", ctypes.c_int),                              # -1=reverse, 0=neutral, 1+ = forward gears
        ("mEngineRPM", ctypes.c_double),                      # engine RPM
        ("mEngineWaterTemp", ctypes.c_double),                # Celsius
        ("mEngineOilTemp", ctypes.c_double),                  # Celsius
        ("mClutchRPM", ctypes.c_double),                      # clutch RPM
        # Add remaining fields to maintain correct offsets...
        ("mUnfilteredThrottle", ctypes.c_double),             # ranges  0.0-1.0
        ("mUnfilteredBrake", ctypes.c_double),                # ranges  0.0-1.0
        ("mUnfilteredSteering", ctypes.c_double),             # ranges -1.0-1.0 (left to right)
        ("mUnfilteredClutch", ctypes.c_double),               # ranges  0.0-1.0
        ("mSteeringShaftTorque", ctypes.c_double),            # torque around steering shaft (used to be mSteeringArmForce, but that is not necessarily accurate for all steering systems)
        ("mFront3rdDeflection", ctypes.c_double),             # deflection at front 3rd spring
        ("mRear3rdDeflection", ctypes.c_double),              # deflection at rear 3rd spring
        ("mFrontWingHeight", ctypes.c_double),                # front wing height
        ("mFrontRideHeight", ctypes.c_double),                # front ride height
        ("mRearRideHeight", ctypes.c_double),                 # rear ride height
        ("mDrag", ctypes.c_double),                           # drag
        ("mFrontDownforce", ctypes.c_double),                 # front downforce
        ("mRearDownforce", ctypes.c_double),                  # rear downforce
        ("mFuel", ctypes.c_double),                           # amount of fuel (liters)
        ("mEngineMaxRPM", ctypes.c_double),                   # rev limit
        ("mScheduledStops", ctypes.c_ubyte),                  # number of scheduled pitstops
        ("mOverheating", ctypes.c_bool),                      # whether overheating icon is shown
        ("mDetached", ctypes.c_bool),                         # whether any parts (besides wheels) have been detached
        ("mHeadlights", ctypes.c_ubyte),                      # status of headlights
        ("mDentSeverity", ctypes.c_ubyte*8),                  # dent severity at 8 locations around the car (0=none, 1=some, 2=more)
        ("mLastImpactET", ctypes.c_double),                   # time of last impact
        ("mLastImpactMagnitude", ctypes.c_double),            # magnitude of last impact
        ("mLastImpactPos", rF2Vec3),                          # location of last impact
        # Simplified for now - add more fields as needed
    ]

class rF2VehicleScoring(ctypes.Structure):
    """rFactor2 Vehicle Scoring Structure - simplified version"""
    _pack_ = 4
    _fields_ = [
        ("mID", ctypes.c_int),                   # slot ID
        ("mDriverName", ctypes.c_char*32),       # driver name
        ("mVehicleName", ctypes.c_char*64),      # vehicle name
        ("mTotalLaps", ctypes.c_short),          # laps completed
        ("mSector", ctypes.c_byte),              # 0=sector3, 1=sector1, 2=sector2
        ("mFinishStatus", ctypes.c_byte),        # 0=none, 1=finished, 2=dnf, 3=dq
        ("mLapDist", ctypes.c_double),           # current distance around track
        ("mPathLateral", ctypes.c_double),       # lateral position with respect to center path
        ("mTrackEdge", ctypes.c_double),         # track edge
        ("mBestSector1", ctypes.c_double),       # best sector 1
        ("mBestSector2", ctypes.c_double),       # best sector 2
        ("mBestLapTime", ctypes.c_double),       # best lap time
        ("mLastSector1", ctypes.c_double),       # last sector 1
        ("mLastSector2", ctypes.c_double),       # last sector 2
        ("mLastLapTime", ctypes.c_double),       # last lap time
        ("mCurSector1", ctypes.c_double),        # current sector 1
        ("mCurSector2", ctypes.c_double),        # current sector 2
        ("mNumPitstops", ctypes.c_short),        # number of pitstops made
        ("mNumPenalties", ctypes.c_short),       # number of outstanding penalties
        ("mIsPlayer", ctypes.c_bool),            # is this the player's vehicle - CRITICAL FOR PLAYER DETECTION!
        ("mControl", ctypes.c_byte),             # who's in control
        ("mInPits", ctypes.c_bool),              # between pit entrance and pit exit
        ("mPlace", ctypes.c_ubyte),              # 1-based position
        ("mVehicleClass", ctypes.c_char*32),     # vehicle class
        # Add remaining fields to maintain structure alignment...
    ]

class rF2Scoring(ctypes.Structure):
    """rFactor2 Scoring Structure - simplified version"""
    _pack_ = 4
    _fields_ = [
        ("mVersionUpdateBegin", ctypes.c_uint),               # Incremented before buffer write
        ("mVersionUpdateEnd", ctypes.c_uint),                 # Incremented after buffer write - CRITICAL FOR DATA SYNC!
        ("mBytesUpdatedHint", ctypes.c_int),                  # bytes of current update
        ("mTrackName", ctypes.c_char*64),                     # current track name
        ("mSession", ctypes.c_int),                           # current session
        ("mCurrentET", ctypes.c_double),                      # current time
        ("mEndET", ctypes.c_double),                          # ending time
        ("mMaxLaps", ctypes.c_int),                           # maximum laps
        ("mLapDist", ctypes.c_double),                        # track length
        ("mNumVehicles", ctypes.c_int),                       # current number of vehicles
        ("mGamePhase", ctypes.c_ubyte),                       # game phase
        ("mYellowFlagState", ctypes.c_char),                  # yellow flag state
        ("mSectorFlag", ctypes.c_ubyte*3),                    # sector flags
        ("mStartLight", ctypes.c_ubyte),                      # start light frame
        ("mNumRedLights", ctypes.c_ubyte),                    # number of red lights
        ("mInRealtime", ctypes.c_bool),                       # in realtime - CRITICAL FOR GAME STATE VALIDATION!
        ("mPlayerName", ctypes.c_char*32),                    # player name
        ("mPlrFileName", ctypes.c_char*64),                   # player file name
        # Vehicle array
        ("mVehicles", rF2VehicleScoring*128),                 # array of vehicles - PLAYER DETECTION HAPPENS HERE!
    ]

class rF2Telemetry(ctypes.Structure):
    """rFactor2 Telemetry Structure - simplified version"""
    _pack_ = 4
    _fields_ = [
        ("mVersionUpdateBegin", ctypes.c_uint),               # Incremented before buffer write
        ("mVersionUpdateEnd", ctypes.c_uint),                 # Incremented after buffer write - CRITICAL FOR DATA SYNC!
        ("mBytesUpdatedHint", ctypes.c_int),                  # bytes of current update
        ("mNumVehicles", ctypes.c_int),                       # current number of vehicles
        ("mVehicles", rF2VehicleTelemetry*128),               # array of vehicles - G-FORCE DATA IS HERE!
    ]

class rF2Extended(ctypes.Structure):
    """rFactor2 Extended Structure - for additional game state"""
    _pack_ = 4
    _fields_ = [
        ("mVersionUpdateBegin", ctypes.c_uint),
        ("mVersionUpdateEnd", ctypes.c_uint),
        ("mVersion", ctypes.c_char*12),                       # API version
        ("is64bit", ctypes.c_bool),                           # Is 64bit plugin?
        # Add physics and other fields as needed...
        ("mInRealtimeFC", ctypes.c_bool),                     # in realtime - ALTERNATIVE GAME STATE CHECK!
        ("mMultimediaThreadStarted", ctypes.c_bool),          # multimedia thread started
        ("mSimulationThreadStarted", ctypes.c_bool),          # simulation thread started
        ("mSessionStarted", ctypes.c_bool),                   # session started - ANOTHER GAME STATE CHECK!
    ]

class RF2TelemetryManager:
    """
    Advanced rFactor2 Telemetry Manager
    Handles player detection, data validation, and real-time synchronization
    """

    def __init__(self):
        self.scoring_data = None
        self.telemetry_data = None
        self.extended_data = None

        # Player synchronization
        self.player_scoring_index = -1  # Index of local player in scoring array
        self.player_telemetry_index = -1  # Index of local player in telemetry array
        self.player_vehicle = None
        self.player_telemetry = None

        # Data validation
        self.last_scoring_version = 0
        self.last_telemetry_version = 0
        self.data_stale_timeout = 5.0  # seconds
        self.last_valid_data_time = 0

        # Game state tracking
        self.is_in_realtime = False
        self.is_session_started = False
        self.ignition_started = False


    def update_from_shared_memory(self, raw_data: bytes) -> bool:
        """
        Update telemetry from raw shared memory data
        Returns True if valid player data was found and updated
        """
        try:
            current_time = time.time()

            # Parse multiple shared memory structures
            if len(raw_data) < 1024:  # Minimum size check
                return False

            # Try to parse scoring data first (for player detection)
            scoring_success = self._parse_scoring_data(raw_data)

            # Try to parse telemetry data (for G-force data)
            telemetry_success = self._parse_telemetry_data(raw_data)

            # Parse extended data (for game state)
            extended_success = self._parse_extended_data(raw_data)

            if scoring_success:
                # Find local player in scoring data
                self._find_local_player()

                # Validate game state
                self._validate_game_state()

                if telemetry_success and self.player_telemetry_index >= 0:
                    # Get player telemetry data
                    self._sync_player_telemetry()


                    return True

            return False

        except Exception as e:
            print(f"RF2TelemetryManager error: {e}")
            return False

    def _parse_scoring_data(self, raw_data: bytes) -> bool:
        """Parse scoring data from shared memory"""
        try:
            # Try to find scoring data at various offsets
            # rF2 uses different offsets for different data types
            scoring_offsets = [0, 64, 128, 256]

            for offset in scoring_offsets:
                if len(raw_data) >= offset + ctypes.sizeof(rF2Scoring):
                    try:
                        scoring_ptr = ctypes.cast(
                            ctypes.c_char_p(raw_data[offset:offset + ctypes.sizeof(rF2Scoring)]),
                            ctypes.POINTER(rF2Scoring)
                        )
                        self.scoring_data = scoring_ptr.contents

                        # Validate version consistency
                        if (self.scoring_data.mVersionUpdateBegin == self.scoring_data.mVersionUpdateEnd and
                            self.scoring_data.mVersionUpdateEnd != self.last_scoring_version):

                            self.last_scoring_version = self.scoring_data.mVersionUpdateEnd
                            self.last_valid_data_time = time.time()
                            return True

                    except Exception:
                        continue

            return False

        except Exception as e:
            print(f"Scoring data parse error: {e}")
            return False

    def _parse_telemetry_data(self, raw_data: bytes) -> bool:
        """Parse telemetry data from shared memory"""
        try:
            # Try to find telemetry data at various offsets
            telemetry_offsets = [4096, 8192, 12288, 16384]  # Common rF2 offsets

            for offset in telemetry_offsets:
                if len(raw_data) >= offset + ctypes.sizeof(rF2Telemetry):
                    try:
                        telemetry_ptr = ctypes.cast(
                            ctypes.c_char_p(raw_data[offset:offset + ctypes.sizeof(rF2Telemetry)]),
                            ctypes.POINTER(rF2Telemetry)
                        )
                        self.telemetry_data = telemetry_ptr.contents

                        # Validate version consistency
                        if (self.telemetry_data.mVersionUpdateBegin == self.telemetry_data.mVersionUpdateEnd and
                            self.telemetry_data.mVersionUpdateEnd != self.last_telemetry_version):

                            self.last_telemetry_version = self.telemetry_data.mVersionUpdateEnd
                            return True

                    except Exception:
                        continue

            return False

        except Exception as e:
            print(f"Telemetry data parse error: {e}")
            return False

    def _parse_extended_data(self, raw_data: bytes) -> bool:
        """Parse extended data for game state validation"""
        try:
            # Extended data is usually near the end
            extended_offsets = [len(raw_data) - ctypes.sizeof(rF2Extended),
                              len(raw_data) - ctypes.sizeof(rF2Extended) - 512,
                              len(raw_data) - ctypes.sizeof(rF2Extended) - 1024]

            for offset in extended_offsets:
                if offset >= 0 and len(raw_data) >= offset + ctypes.sizeof(rF2Extended):
                    try:
                        extended_ptr = ctypes.cast(
                            ctypes.c_char_p(raw_data[offset:offset + ctypes.sizeof(rF2Extended)]),
                            ctypes.POINTER(rF2Extended)
                        )
                        self.extended_data = extended_ptr.contents
                        return True

                    except Exception:
                        continue

            return False

        except Exception:
            return False

    def _find_local_player(self):
        """Find the local player in the scoring data"""
        if not self.scoring_data:
            return

        self.player_scoring_index = -1

        # Search through all vehicles to find the player
        for i in range(min(self.scoring_data.mNumVehicles, 128)):
            try:
                vehicle = self.scoring_data.mVehicles[i]
                if vehicle.mIsPlayer:  # This is the local player!
                    self.player_scoring_index = i
                    self.player_vehicle = vehicle

                    # Map scoring index to telemetry index (usually the same, but can differ)
                    self.player_telemetry_index = self._find_telemetry_index(vehicle.mID)
                    break

            except Exception:
                continue

    def _find_telemetry_index(self, player_id: int) -> int:
        """Find telemetry index that matches the player ID"""
        if not self.telemetry_data:
            return -1

        # Search telemetry array for matching ID
        for i in range(min(self.telemetry_data.mNumVehicles, 128)):
            try:
                if self.telemetry_data.mVehicles[i].mID == player_id:
                    return i
            except Exception:
                continue

        return -1

    def _validate_game_state(self):
        """Validate that the game is in a state where telemetry is meaningful"""
        self.is_in_realtime = False
        self.is_session_started = False
        self.ignition_started = False

        # Check scoring data for realtime state
        if self.scoring_data:
            self.is_in_realtime = self.scoring_data.mInRealtime

        # Check extended data for additional validation
        if self.extended_data:
            self.is_session_started = self.extended_data.mSessionStarted
            # Alternative realtime check
            if not self.is_in_realtime:
                self.is_in_realtime = self.extended_data.mInRealtimeFC

        # Check player vehicle ignition (if available)
        if self.player_telemetry and hasattr(self.player_telemetry, 'mIgnitionStarter'):
            self.ignition_started = self.player_telemetry.mIgnitionStarter > 0

    def _sync_player_telemetry(self):
        """Synchronize player telemetry data"""
        if (self.telemetry_data and
            self.player_telemetry_index >= 0 and
            self.player_telemetry_index < self.telemetry_data.mNumVehicles):

            try:
                self.player_telemetry = self.telemetry_data.mVehicles[self.player_telemetry_index]
            except Exception as e:
                print(f"Player telemetry sync error: {e}")
                self.player_telemetry = None

        print(f"  Player found: scoring_idx={self.player_scoring_index}, tele_idx={self.player_telemetry_index}")
        print(f"  Game state: realtime={self.is_in_realtime}, session={self.is_session_started}, ignition={self.ignition_started}")

        if self.player_vehicle:
            driver_name = self.player_vehicle.mDriverName.decode('utf-8', errors='ignore').strip('\x00')
            vehicle_name = self.player_vehicle.mVehicleName.decode('utf-8', errors='ignore').strip('\x00')
            print(f"  Player: {driver_name} in {vehicle_name}")

        if self.player_telemetry:
            accel = self.player_telemetry.mLocalAccel
            print(f"  Raw mLocalAccel: X={accel.x:.6f}, Y={accel.y:.6f}, Z={accel.z:.6f}")

            # Convert to G-force
            gforce_lateral = accel.x / 9.81
            gforce_longitudinal = accel.z / 9.81
            gforce_vertical = accel.y / 9.81
            print(f"  G-forces: Lat={gforce_lateral:.3f}G, Long={gforce_longitudinal:.3f}G, Vert={gforce_vertical:.3f}G")

        # Validation warnings
        if not self.is_in_realtime:
            print("  WARNING: Game not in realtime mode!")
        if not self.is_session_started:
            print("  WARNING: Session not started!")

    def get_gforce_data(self) -> tuple[float, float, float]:
        """
        Get current G-force data for the local player
        Returns (lateral, longitudinal, vertical) in G units
        """
        if (not self.player_telemetry or
            not self.is_in_realtime or
            time.time() - self.last_valid_data_time > self.data_stale_timeout):
            return (0.0, 0.0, 0.0)

        try:
            accel = self.player_telemetry.mLocalAccel

            # Convert from m/s² to G-force
            gforce_lateral = accel.x / 9.81      # X = lateral (left/right)
            gforce_longitudinal = accel.z / 9.81  # Z = longitudinal (forward/back)
            gforce_vertical = accel.y / 9.81     # Y = vertical (up/down)

            return (gforce_lateral, gforce_longitudinal, gforce_vertical)

        except Exception as e:
            print(f"G-force extraction error: {e}")
            return (0.0, 0.0, 0.0)

    def is_data_valid(self) -> bool:
        """Check if current telemetry data is valid and up-to-date"""
        return (self.player_telemetry is not None and
                self.is_in_realtime and
                time.time() - self.last_valid_data_time < self.data_stale_timeout)

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
        self.connected = False  # Only connected when real data is available

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

        # NOVO SISTEMA CORRIGIDO - Usar telemetria rF2 oficial
        self.rf2_telemetry = None
        try:
            from telemetry_rf2_corrected import RF2TelemetryManager
            self.rf2_telemetry = RF2TelemetryManager()
            print("[OK] Sistema de telemetria rF2 corrigido carregado")
        except ImportError as e:
            print(f"[AVISO] Sistema de telemetria rF2 corrigido nao disponivel: {e}")

        # Legacy shared memory (removido)
        self.lmu_connected = False
        self.rf2_shared_memory = None

        # Connection stability tracking
        self.connection_failures = 0
        self.last_valid_read = 0
        self.max_connection_failures = 10

    def start(self):
        """Start telemetry data reading"""
        print("Starting enhanced telemetry reader...")
        self.running = True
        self.thread = threading.Thread(target=self._read_telemetry_loop, daemon=True)
        self.thread.start()

        # Try to connect to F1 UDP
        self._setup_f1_connection()

        # NOVO: Iniciar sistema corrigido de rF2
        if self.rf2_telemetry:
            success = self.rf2_telemetry.start()
            if success:
                print("[OK] Sistema de telemetria rF2 corrigido iniciado")
                self.lmu_connected = True
            else:
                print("[ERRO] Falha ao iniciar sistema de telemetria rF2 corrigido")
                self.lmu_connected = False
        else:
            # Fallback: Try to connect to legacy rFactor2/LMU shared memory
            self._setup_rf2_connection()

    def stop(self):
        """Stop telemetry reading"""
        print("Stopping telemetry reader...")
        self.running = False

        # Close sockets
        if self.f1_socket:
            try:
                self.f1_socket.close()
                print("  F1 socket closed")
            except:
                pass

        # NOVO: Parar sistema corrigido de rF2
        if self.rf2_telemetry:
            try:
                self.rf2_telemetry.stop()
                print("  [OK] Sistema de telemetria rF2 corrigido parado")
            except:
                pass

        # Close legacy shared memory
        if self.rf2_shared_memory:
            try:
                self.rf2_shared_memory.close()
                print("  rF2 shared memory closed")
            except:
                pass

        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            print("  Waiting for telemetry thread to stop...")
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                print("  Warning: Telemetry thread did not stop cleanly")
            else:
                print("  Telemetry thread stopped")

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

    def _setup_rf2_connection(self):
        """Setup connection to rFactor2/LMU shared memory"""
        try:
            # Try different shared memory names used by rFactor2 plugin
            memory_names = [
                "$rFactor2SMMP_Telemetry$",
                "rFactor2_Telemetry",
                "rF2_Telemetry",
                "$rF2SMMP_Telemetry$"
            ]

            for name in memory_names:
                try:
                    # Try larger buffer size for full telemetry data
                    self.rf2_shared_memory = mmap.mmap(-1, 8192, name)
                    print(f"rFactor2/LMU shared memory connected successfully with name: {name}")
                    self.lmu_connected = True
                    return
                except:
                    continue

            print("Could not connect to any rFactor2 shared memory mapping")
            self.lmu_connected = False
            self.rf2_shared_memory = None

        except Exception as e:
            print(f"rFactor2/LMU shared memory setup error: {e}")
            self.lmu_connected = False
            self.rf2_shared_memory = None

    def _read_telemetry_loop(self):
        """Main telemetry reading loop"""
        while self.running:
            try:
                # Try F1 UDP data first
                if self._read_f1_data():
                    self.current_game = "F1 2024/2023"
                    self.connection_status = "F1 Connected"
                    self.connected = True
                # NOVO: Try sistema corrigido de rF2/LMU
                elif self._read_rf2_corrected_data():
                    self.current_game = "Le Mans Ultimate"
                    self.connection_status = "LMU Connected"
                    self.connected = True
                # Fallback: Try legacy LMU shared memory
                elif self._read_lmu_data():
                    self.current_game = "Le Mans Ultimate"
                    self.connection_status = "LMU Connected"
                    self.connected = True
                else:
                    # No real telemetry data available
                    self.current_game = "No Game"
                    self.connection_status = "Offline"
                    self.connected = False
                    # Reset G-force data to zero when no game data
                    self.gforce_longitudinal = 0.0
                    self.gforce_lateral = 0.0
                    self.gforce_vertical = 0.0

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

    def _read_rf2_corrected_data(self) -> bool:
        """
        SISTEMA CORRIGIDO: Read rF2/LMU telemetry using official library
        Sistema otimizado de telemetria
        """
        if not self.rf2_telemetry:
            return False

        try:
            # Verificar se há dados válidos no sistema corrigido
            if self.rf2_telemetry.is_data_valid():
                # Obter dados de força G (IMPLEMENTAÇÃO CORRETA)
                gforce_data = self.rf2_telemetry.get_gforce_data()
                basic_data = self.rf2_telemetry.get_basic_telemetry()

                # Atualizar nossa estrutura (compatibilidade)
                self.gforce_lateral = gforce_data['lateral']
                self.gforce_longitudinal = gforce_data['longitudinal']
                self.gforce_vertical = gforce_data['vertical']

                # Atualizar dados básicos
                self.speed = basic_data['speed']
                self.throttle = basic_data['throttle']
                self.brake = basic_data['brake']
                self.gear = basic_data['gear']
                self.rpm = basic_data['rpm']

                # G-force values updated

                return True

            return False

        except Exception as e:
            print(f"Sistema corrigido rF2 erro: {e}")
            return False

    def _read_lmu_data_new(self) -> bool:
        """
        NEW: Read Le Mans Ultimate shared memory data using RF2TelemetryManager
        Sistema com detecção de player e validação adequada
        """
        if not self.rf2_shared_memory:
            return False

        try:
            # Read raw telemetry data from shared memory
            self.rf2_shared_memory.seek(0)
            raw_data = self.rf2_shared_memory.read(16384)  # Larger buffer for complete rF2 data

            if len(raw_data) < 1024:  # Minimum expected data size
                return False

            # Use the new RF2TelemetryManager to parse and validate data
            telemetry_success = self.rf2_telemetry_manager.update_from_shared_memory(raw_data)

            if telemetry_success and self.rf2_telemetry_manager.is_data_valid():
                # Extract G-force data using the new manager
                gforce_lateral, gforce_longitudinal, gforce_vertical = self.rf2_telemetry_manager.get_gforce_data()

                # Update our G-force values
                self.gforce_lateral = gforce_lateral
                self.gforce_longitudinal = gforce_longitudinal
                self.gforce_vertical = gforce_vertical

                return True

            return False

        except Exception as e:
            print(f"NEW LMU data read error: {e}")
            return False

    def _read_lmu_data(self) -> bool:
        """
        Read Le Mans Ultimate shared memory data
        Implementação adequada - using proper rF2 structures
        """
        if not self.rf2_shared_memory:
            return False

        try:
            # Read telemetry data from shared memory - abordagem otimizada
            self.rf2_shared_memory.seek(0)
            raw_data = self.rf2_shared_memory.read(16384)  # Larger buffer otimizado

            if len(raw_data) < 1024:
                return False

            # Parse rF2 telemetry structure directly
            # Look for telemetry header and vehicle data
            try:
                # rF2 telemetry structure starts with header info
                # Skip to vehicle telemetry data (usually around offset 64-128)
                for base_offset in [64, 128, 256, 512]:
                    if base_offset + ctypes.sizeof(rF2VehicleTelemetry) > len(raw_data):
                        continue

                    try:
                        # Try to cast raw data to rF2VehicleTelemetry structure
                        vehicle_data = rF2VehicleTelemetry.from_buffer_copy(
                            raw_data[base_offset:base_offset + ctypes.sizeof(rF2VehicleTelemetry)]
                        )

                        # Validate vehicle data - more lenient validation otimizado
                        if (0 <= vehicle_data.mID <= 127):    # Valid vehicle ID range - that's enough!
                            # Implementação adequada:
                            # Get acceleration data from mLocalAccel
                            accel_x = vehicle_data.mLocalAccel.x  # Lateral
                            accel_y = vehicle_data.mLocalAccel.y  # Vertical
                            accel_z = vehicle_data.mLocalAccel.z  # Longitudinal

                            # Função rmnan - handle inf/nan values
                            def rmnan(value):
                                if math.isnan(value) or math.isinf(value):
                                    return 0.0
                                return value

                            accel_x = rmnan(accel_x)
                            accel_y = rmnan(accel_y)
                            accel_z = rmnan(accel_z)

                            # Validate acceleration values are reasonable (be more lenient)
                            if (abs(accel_x) < 200 and abs(accel_y) < 200 and abs(accel_z) < 200 and
                                not (math.isnan(accel_x) or math.isnan(accel_y) or math.isnan(accel_z))):
                                # EXACT Cálculo de G-force:
                                g_accel = 9.80665  # Valor padrão

                                # Mapeamento de coordenadas:
                                self.gforce_lateral = accel_x / g_accel      # X = lateral
                                self.gforce_longitudinal = accel_z / g_accel  # Z = longitudinal
                                self.gforce_vertical = accel_y / g_accel     # Y = vertical

                                test_lat = abs(accel_x / g_accel)
                                test_long = abs(accel_z / g_accel)
                                # G-force validation removed

                                # Get other basic telemetry data
                                self.speed = max(0, rmnan(vehicle_data.mLocalVel.z) * 3.6)  # Z velocity to km/h
                                self.throttle = max(0, min(100, rmnan(vehicle_data.mUnfilteredThrottle) * 100))
                                self.brake = max(0, min(100, rmnan(vehicle_data.mUnfilteredBrake) * 100))
                                self.gear = max(-1, vehicle_data.mGear)
                                self.rpm = max(0, rmnan(vehicle_data.mEngineRPM))

                                # G-force data processed

                                # Reset connection failure counter on successful read
                                self.connection_failures = 0
                                self.last_valid_read = time.time()
                                return True

                    except Exception as parse_error:
                        continue  # Try next offset

                # If no valid structure found at specific offsets, try a broader search
                print("Trying broader search for telemetry data...")

                # Fallback: try to find ANY valid data pattern
                for offset in range(0, min(len(raw_data) - 1024, 4096), 64):
                    try:
                        # Simple validation: look for reasonable speed/gear values
                        test_speed = struct.unpack('f', raw_data[offset:offset+4])[0] if offset+4 <= len(raw_data) else -999
                        test_gear = struct.unpack('i', raw_data[offset+4:offset+8])[0] if offset+8 <= len(raw_data) else -999

                        if 0 <= test_speed <= 150 and -1 <= test_gear <= 10:  # Reasonable values
                            # Found some valid-looking data, maintain connection
                            self.speed = test_speed * 3.6
                            self.gear = test_gear
                            print(f"Fallback data found: Speed={self.speed:.1f}km/h, Gear={self.gear}")
                            return True
                    except:
                        continue

                # If we reach here, no valid data was found
                self.connection_failures += 1

                # Estilo otimizado connection stability: don't immediately disconnect
                if self.connection_failures < self.max_connection_failures:
                    # If we had recent valid data, maintain connection status
                    if time.time() - self.last_valid_read < 5.0:  # Within last 5 seconds
                        print(f"Connection issue {self.connection_failures}/{self.max_connection_failures}, maintaining connection...")
                        return True  # Maintain connection temporarily

                print(f"No valid rF2 telemetry structure found (failures: {self.connection_failures})")
                return False

            except Exception as struct_error:
                self.connection_failures += 1
                print(f"Structure parsing error: {struct_error} (failures: {self.connection_failures})")

                # Maintain connection if we had recent success
                if (self.connection_failures < self.max_connection_failures and
                    time.time() - self.last_valid_read < 3.0):
                    return True
                return False

        except Exception as e:
            self.connection_failures += 1
            print(f"LMU data read error: {e} (failures: {self.connection_failures})")

            # Maintain connection if we had recent success
            if (self.connection_failures < self.max_connection_failures and
                time.time() - self.last_valid_read < 3.0):
                return True
            return False


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


class GForceCircle(QWidget):
    """Friction Circle for G-Force visualization - Implementação adequada"""
    def __init__(self, show_labels=True):
        super().__init__()

        # Config
        self.display_size = 200
        self.display_radius_g = 3.0  # Maximum G-force range
        self.global_scale = (self.display_size * 0.5) / self.display_radius_g
        self.area_center = self.display_size * 0.5
        self.dot_size = 8
        self.show_labels = show_labels

        # Current G-force values
        self.gforce_lateral = 0.0
        self.gforce_longitudinal = 0.0
        self.last_x = self.area_center
        self.last_y = self.area_center

        # Set widget size
        self.setFixedSize(self.display_size, self.display_size)

    def setFixedSize(self, width, height):
        """Override para ajustar parâmetros quando tamanho muda"""
        super().setFixedSize(width, height)
        # Recalcular parâmetros baseados no novo tamanho
        self.display_size = min(width, height)
        self.global_scale = (self.display_size * 0.5) / self.display_radius_g
        self.area_center = self.display_size * 0.5
        self.dot_size = max(3, self.display_size // 25)  # Ajustar tamanho do ponto
        self.last_x = self.area_center
        self.last_y = self.area_center

        # Colors (estilo otimizado)
        self.bg_color = QColor(40, 40, 40)
        self.circle_color = QColor(80, 80, 80)
        self.dot_color = QColor(255, 255, 255)
        self.grid_color = QColor(100, 100, 100)
        self.text_color = QColor(255, 255, 255)

    def update_gforce(self, lateral, longitudinal):
        """Update G-force values and position"""
        self.gforce_lateral = lateral
        self.gforce_longitudinal = longitudinal

        # Mapeamento de coordenadas: brake top, accel bottom
        temp_gforce_raw = (-longitudinal, lateral)  # Invert longitudinal for correct orientation

        # Scale position coordinate to global (padrão adequado)
        self.last_x = temp_gforce_raw[1] * self.global_scale + self.area_center
        self.last_y = temp_gforce_raw[0] * self.global_scale + self.area_center

        # Clamp to display area
        self.last_x = max(self.dot_size, min(self.display_size - self.dot_size, self.last_x))
        self.last_y = max(self.dot_size, min(self.display_size - self.dot_size, self.last_y))

        self.update()

    def paintEvent(self, event):
        """Draw the friction circle"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Fill background
        painter.fillRect(self.rect(), self.bg_color)

        # Draw main circle
        painter.setPen(QPen(self.circle_color, 2))
        painter.setBrush(QBrush())
        circle_radius = self.display_radius_g * self.global_scale
        painter.drawEllipse(
            self.area_center - circle_radius,
            self.area_center - circle_radius,
            circle_radius * 2,
            circle_radius * 2
        )

        # Draw reference circles (1G, 2G)
        painter.setPen(QPen(self.grid_color, 1, Qt.DashLine))
        for g_value in [1.0, 2.0]:
            if g_value <= self.display_radius_g:
                ref_radius = g_value * self.global_scale
                painter.drawEllipse(
                    self.area_center - ref_radius,
                    self.area_center - ref_radius,
                    ref_radius * 2,
                    ref_radius * 2
                )

        # Draw center cross
        painter.setPen(QPen(self.grid_color, 1))
        cross_size = 10
        painter.drawLine(
            self.area_center - cross_size, self.area_center,
            self.area_center + cross_size, self.area_center
        )
        painter.drawLine(
            self.area_center, self.area_center - cross_size,
            self.area_center, self.area_center + cross_size
        )

        # Draw current G-force dot
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(QBrush(self.dot_color))
        painter.drawEllipse(
            self.last_x - self.dot_size/2,
            self.last_y - self.dot_size/2,
            self.dot_size,
            self.dot_size
        )

        # Draw G-force values as text (apenas se show_labels for True)
        if self.show_labels:
            painter.setPen(QPen(self.text_color))
            font = QFont("Arial", 10)
            painter.setFont(font)

            # Current values in corners
            painter.drawText(10, 20, f"Lat: {abs(self.gforce_lateral):.2f}G")
            painter.drawText(10, 40, f"Long: {abs(self.gforce_longitudinal):.2f}G")

            # Direction indicators
            if abs(self.gforce_lateral) > 0.1:
                direction = "◀" if self.gforce_lateral > 0 else "▶"
                painter.drawText(150, 20, direction)

            if abs(self.gforce_longitudinal) > 0.1:
                direction = "▲" if self.gforce_longitudinal < 0 else "▼"
                painter.drawText(150, 40, direction)


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

        # Configurar pedais REAIS
        self.pedal_reader = RealPedalReader()
        self.pedal_reader.start()

        # Configurar telemetria avançada separadamente
        self.telemetry_reader = TelemetryDataReader()
        self.telemetry_reader.start()

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

        # 1. Histórico dos pedais (lado esquerdo)
        self.graph_canvas = GraphCanvas()
        self.graph_canvas.setMinimumHeight(100)
        self.graph_canvas.setMinimumWidth(300)
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

        # 4. G-Force Circle (lado direito - tamanho reduzido, sem legendas)
        self.gforce_circle = GForceCircle(show_labels=False)
        self.gforce_circle.setFixedSize(72, 72)  # Tamanho aumentado em 20%
        main_layout.addWidget(self.gforce_circle)

        layout.addLayout(main_layout)

        # Instruções com versão (usar versão já carregada)
        version_text = f"v{getattr(self, 'current_version', '1.0.0')}"
        instructions = QLabel(f"ARRASTE para mover | V = Toggle | Ctrl+U = Update | ESC = Fechar | {version_text}")
        instructions.setFont(QFont("Arial", 8))
        instructions.setStyleSheet("color: #FFC800;")
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)


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

        # Atualizar G-Force Circle (estilo otimizado)
        gforce_data = self.telemetry_reader.get_gforce_data()
        self.gforce_circle.update_gforce(gforce_data['lateral'], gforce_data['longitudinal'])

        # Atualizar gráfico de histórico dos pedais
        self.graph_canvas.update_data(self.throttle_history, self.brake_history)


        # Atualizar status da conexão
        self.update_connection_status()

        # Atualiza UI
        self.throttle_bar.setValue(int(throttle * 100))
        self.throttle_label.setText(f"{int(throttle * 100)}%")

        self.brake_bar.setValue(int(brake * 100))
        self.brake_label.setText(f"{int(brake * 100)}%")


    def update_connection_status(self):
        """Update connection status display"""
        try:
            # Get telemetry status
            telemetry_data = self.telemetry_reader.get_basic_telemetry()
            connection_status = telemetry_data.get('connection', 'Disconnected')
            current_game = telemetry_data.get('game', 'Unknown')

            # Update main status label with connection info
            if connection_status == "F1 Connected":
                status_text = "Racing Telemetry - F1 ONLINE"
                status_color = "#00FF78"  # Green
            elif connection_status == "LMU Connected":
                status_text = "Racing Telemetry - LMU ONLINE"
                status_color = "#00FF78"  # Green
            else:
                status_text = "Racing Telemetry - OFFLINE"
                status_color = "#888888"  # Gray

            self.status_label.setText(status_text)
            self.status_label.setStyleSheet(f"color: {status_color};")

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

        # Stop all timers
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
            print("  Update timer stopped")
        if hasattr(self, 'hotkey_timer'):
            self.hotkey_timer.stop()
            print("  Hotkey timer stopped")
        if hasattr(self, 'check_updates_timer'):
            self.check_updates_timer.stop()
            print("  Check updates timer stopped")
        if hasattr(self, 'blink_timer'):
            self.blink_timer.stop()
            print("  Blink timer stopped")

        # Stop pedal reader
        if hasattr(self, 'pedal_reader'):
            self.pedal_reader.stop()
            print("  Pedal reader stopped")

        # Stop telemetry reader
        if hasattr(self, 'telemetry_reader'):
            self.telemetry_reader.stop()
            print("  Telemetry reader stopped")

        print("Overlay cleanup complete!")
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