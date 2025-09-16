# 🏎️ Racing Telemetry Pedals

Aplicação em tempo real para monitoramento de telemetria dos pedais de aceleração e freio para Le Mans Ultimate e F1.

## 🎯 Características Principais

- ✅ **Le Mans Ultimate** - Suporte nativo via UDP
- ✅ **F1 2023/2024** - Telemetria completa dos pedais
- ✅ **Interface moderna** - Barras e gráficos em tempo real
- ✅ **Histórico visual** - Últimos 10 segundos de dados
- ✅ **Auto-detecção** - Detecta automaticamente o jogo
- ✅ **Performance otimizada** - 60 FPS fluidos

## 🚀 Como Usar

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Executar

**Overlay Compacto (Recomendado para Gaming):**

```bash
python overlay.py
```

**Interface Completa:**

```bash
python src/main.py
```

### 3. Configurar o jogo

**Le Mans Ultimate:**
⚠️ **REQUER PLUGIN** - Veja instruções detalhadas em [SETUP_LMU.md](SETUP_LMU.md)

1. Baixe `rFactor2SharedMemoryMapPlugin64.dll`
2. Copie para `Le Mans Ultimate\Plugins\`
3. Edite `CustomPluginVariables.JSON`
4. **Configure o jogo em modo BORDERLESS** (não fullscreen)
5. Reinicie o jogo

**F1 2023/2024:**

1. Settings > Telemetry Settings
2. UDP Telemetry: ON
3. IP Address: 127.0.0.1
4. Port: 20777
5. Send Rate: 60Hz

### 4. Correr!

- Entre em qualquer sessão (treino, qualifying, corrida)
- Os dados aparecerão automaticamente na interface

## 🎮 Controles

**Interface Completa:**

- **ESC**: Sair da aplicação
- **SPACE**: Reset do histórico de dados

**Overlay Compacto:**

- **Mouse**: Arrastar para mover overlay
- **F11**: Toggle always on top
- **Ctrl+D**: Toggle transparência
- **Ctrl+U**: Verificar atualizações
- **ESC**: Sair

## 📊 Interface

- **Barras dos pedais**: Mostram % atual de throttle/brake
- **Gráfico histórico**: Últimos 10 segundos de telemetria
- **Status da conexão**: Indica se está recebendo dados
- **Contador de packets**: Para monitorar performance

## 🔄 Atualizações Automáticas

O projeto possui sistema de auto-update integrado:

- **Verificação automática**: No startup da aplicação
- **Verificação manual**: Use **Ctrl+U** no overlay
- **Download automático**: Interface gráfica para baixar novas versões
- **Instalação**: Processo automatizado com backup

### Para Desenvolvedores

Para criar um novo release:

```bash
# Atualizar versão e criar release
python create_release.py 1.1.0 "Descrição das mudanças"

# Seguir instruções no terminal para publicar no GitHub
```

⚠️ **Importante**: Edite `version.py` e configure seu repositório GitHub antes de usar.

## 🔧 Configuração Avançada

Edite `configs/games_config.py` para ajustar portas ou adicionar novos jogos.

## ❗ Troubleshooting

**Sem dados aparecendo:**

1. Verifique se a telemetria está habilitada no jogo
2. Confirme porta e IP corretos
3. **Para LMU: Certifique-se que o jogo está em modo BORDERLESS**
4. **Para LMU: Verifique se o plugin `rFactor2SharedMemoryMapPlugin64.dll` está instalado**
5. Desabilite firewall temporariamente
6. Reinicie o jogo após configurar

**Performance baixa:**

- Reduza send rate do jogo para 30Hz
- Feche outros programas pesados

## 🎯 Jogos Suportados

| Jogo             | Método                 | Status      |
| ---------------- | ---------------------- | ----------- |
| Le Mans Ultimate | Shared Memory + Plugin | ✅ Completo |
| F1 2024          | UDP (porta 20777)      | ✅ Completo |
| F1 2023          | UDP (porta 20777)      | ✅ Completo |

## 🚧 Próximas Features

- [ ] Suporte para Assetto Corsa Competizione
- [ ] Gravação de sessões
- [ ] Análise de consistência
- [ ] Export para MoTeC i2

---

Desenvolvido com ❤️ para a comunidade sim racing
