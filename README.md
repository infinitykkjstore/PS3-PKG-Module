# PS3-Pkg-Module

Extrai o conteudo de arquivos `.pkg` do PS3 (e PSP) diretamente de uma URL ou de um arquivo local.

Funciona com **PKGs finalized** (revisao `0x8000`) e **non-finalized**, tanto PS3 (tipo 1) quanto PSP (tipo 2).

## Requisitos

- Python 3.6+
- `pycryptodome` (para AES-CTR em PKGs finalized)

```bash
pip install pycryptodome
```

Sem o `pycryptodome` o script ainda funciona para PKGs non-finalized.

## Uso basico

```bash
python main.py <caminho_ou_url_do_pkg>
```

### De uma URL direta (recomendado)

O PKG e baixado sob demanda via `Range requests` — apenas as partes necessarias sao transferidas, sem baixar o arquivo inteiro.

```bash
python main.py "http://zeus.dl.playstation.net/cdn/UP0177/NPUB30443_00/Hty...pkg"
```

### De um arquivo local

```bash
python main.py Sonic_the_Hedgehog_2.pkg
```

## Opcoes

| Flag | Descricao |
|------|-----------|
| `--full` | Extrai **todos** os arquivos do PKG com a estrutura de pastas original (comportamento padrao) |
| `--sfo` | Extrai apenas o `PARAM.SFO` (raiz do PKG) — sem criar pastas |
| `--eboot` | Extrai apenas o `EBOOT.BIN` (`USRDIR/EBOOT.BIN`) — sem criar pastas |
| `--pic1` | Extrai apenas o `PIC1.PNG` (raiz) — sem criar pastas |
| `--pic0` | Extrai apenas o `PIC0.PNG` (raiz) — sem criar pastas |
| `--icon` | Extrai apenas o `ICON0.PNG` (raiz) — sem criar pastas |
| `--path CAMINHO` | Extrai qualquer arquivo especifico informando o caminho dentro do PKG (ex: `/USRDIR/EBOOT.BIN`) — sem criar pastas |
| `-o DIR` / `--output DIR` | Diretorio de saida (padrao: `PS3`) |

Todas as flags de modo sao **mutuamente exclusivas**: use apenas uma por vez.

## Exemplos

### Extrair tudo (modo padrao)

```bash
python main.py "http://cdn.example.com/game.pkg"
```

Saida:
```
Platform: PS3
Finalized: True
Content ID: UP0177-NPUB30443_00-SVCSONIC2XXXXXXX
Items: 16
Total: 35433776 bytes
Extraidos 12 arquivo(s) de todos para C:\...\PS3
```

Estrutura criada:
```
PS3/
├── ICON0.PNG
├── PARAM.SFO
├── PIC0.PNG
├── PIC1.PNG
├── PIC2.PNG
├── PS3LOGO.DAT
├── TROPDIR/NPWR00587_00/TROPHY.TRP
└── USRDIR/
    ├── EBOOT.BIN
    ├── GAMEDATA1.EDAT
    ├── RIBBON.MP4
    └── 0B/
        ├── SONIC2.SR
        └── SONIC2_FW.SR
```

### Extrair apenas PARAM.SFO

```bash
python main.py "http://cdn.example.com/game.pkg" --sfo
```

Saida: apenas `PS3/PARAM.SFO` (sem subpastas).

### Extrair apenas EBOOT.BIN

```bash
python main.py "http://cdn.example.com/game.pkg" --eboot
```

Saida: apenas `PS3/EBOOT.BIN` (sem subpastas).

### Extrair apenas ICON0.PNG

```bash
python main.py "http://cdn.example.com/game.pkg" --icon
```

Saida: apenas `PS3/ICON0.PNG`.

### Extrair arquivo especifico com --path

```bash
# Arquivo na raiz
python main.py "http://cdn.example.com/game.pkg" --path /ICON0.PNG

# Arquivo em subdiretorio
python main.py "http://cdn.example.com/game.pkg" --path /USRDIR/0B/SONIC2.SR

# Caminho sem a barra inicial tambem funciona
python main.py "http://cdn.example.com/game.pkg" --path USRDIR/EBOOT.BIN
```

Se o caminho informado nao existir dentro do PKG, o erro e exibido:
```
[ERRO] Falha na extracao: Arquivo "USRDIR/NAO_EXISTE.DAT" nao encontrado no PKG
```

### Diretorio de saida customizado

```bash
python main.py "http://cdn.example.com/game.pkg" --sfo -o minha_pasta
```

## Dica para Windows (Git Bash / MSYS2)

No Git Bash, caminhos que comecam com `/` (ex: `--path /ICON0.PNG`) sao convertidos automaticamente pelo shell para caminhos absolutos do Windows (ex: `C:\Program Files\Git\ICON0.PNG`).

O script detecta essa conversao e recupera o caminho original automaticamente. Voce pode usar com seguranca:

```bash
python main.py "http://cdn.example.com/game.pkg" --path /ICON0.PNG
```

## Como funciona

1. **Leitura do cabecalho** (offset `0x00`): magic `7F PKG`, revisao, tipo, Content ID, IV, digest
2. **Tabela de arquivos criptografada**: o offset da tabela esta nos primeiros 16 bytes decryptados. Cada entrada tem 32 bytes: `name_offset | name_size | padding | file_offset | file_size | flags`
3. **Descriptografia**:
   - **Finalized** (`revision == 0x8000`): AES-128-CTR com chave fixa do PS3/PSP e IV do cabecalho
   - **Non-finalized**: cifra baseada em SHA-1 com o digest do cabecalho
4. **Extracao**: itera sobre a tabela, descriptografa nomes e dados, e escreve os arquivos no disco

## Licenca

MIT
