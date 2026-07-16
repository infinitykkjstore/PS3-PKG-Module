# PS3-PKG-Module

Ferramenta completa para extrair e criar arquivos `.pkg` do PS3 (e PSP).

**Extração**: suporta PKGs finalized (`0x8000`) e non-finalized, PS3 (tipo 1) e PSP (tipo 2), de URL ou arquivo local.

**Construção**: monta PKGs customizados a partir de uma estrutura de diretórios que espelha o HDD do PS3.

## Requisitos

- Python 3.6+
- `pycryptodome` (opcional — AES-CTR para PKGs finalized)

```bash
pip install pycryptodome
```

Sem o `pycryptodome` o script funciona para PKGs non-finalized e para construir PKGs.

## Instalação

Clone o repositório:

```bash
git clone https://github.com/fogueira8327/PS3-PKG-Module.git
cd PS3-PKG-Module
```

### Aceleração C (opcional, recomendado)

Compila a extensão nativa `pkgcrypt` para acelerar drasticamente a descriptografia de PKGs non-finalized:

```bash
python build_deps.py
```

A extensão será detectada automaticamente na proxima execução.

## Extração (`main.py`)

### Uso básico

```bash
python main.py <caminho_ou_url_do_pkg>
```

### De uma URL direta (recomendado)

O PKG é baixado sob demanda via `Range requests` — apenas as partes necessárias são transferidas, sem baixar o arquivo inteiro.

```bash
python main.py "http://zeus.dl.playstation.net/cdn/UP0177/NPUB30443_00-Hty...pkg"
```

### De um arquivo local

```bash
python main.py Sonic_the_Hedgehog_2.pkg
```

### Opções

| Flag | Descrição |
|------|-----------|
| `--full` | Extrai **todos** os arquivos do PKG com a estrutura de pastas original (comportamento padrão) |
| `--sfo` | Extrai apenas o `PARAM.SFO` (raiz do PKG) — sem criar pastas |
| `--eboot` | Extrai apenas o `EBOOT.BIN` (`USRDIR/EBOOT.BIN`) — sem criar pastas |
| `--pic1` | Extrai apenas o `PIC1.PNG` (raiz) — sem criar pastas |
| `--pic0` | Extrai apenas o `PIC0.PNG` (raiz) — sem criar pastas |
| `--icon` | Extrai apenas o `ICON0.PNG` (raiz) — sem criar pastas |
| `--path CAMINHO` | Extrai qualquer arquivo específico informando o caminho dentro do PKG (ex: `/USRDIR/EBOOT.BIN`) — sem criar pastas |
| `--content-id` | Apenas exibe o Content ID do PKG e sai — **não extrai nada** |
| `-o DIR` / `--output DIR` | Diretório de saída (padrão: `PS3`) |

Todas as flags de modo (exceto `-o`) são **mutuamente exclusivas**: use apenas uma por vez.

### Exemplos

#### Extrair tudo (modo padrão)

```bash
python main.py "http://cdn.example.com/game.pkg"
```

Saída:
```
Platform: PS3
Finalized: True
Content ID: UP0177-NPUB30443_00-SVCSONIC2XXXXXXX
Items: 16
Total: 35433776 bytes
Source: http://cdn.example.com/game.pkg
Extraidos 12 arquivo(s) de todos para /home/user/PS3
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

#### Extrair apenas PARAM.SFO

```bash
python main.py "http://cdn.example.com/game.pkg" --sfo
```

#### Extrair apenas EBOOT.BIN

```bash
python main.py "http://cdn.example.com/game.pkg" --eboot
```

#### Extrair apenas ICON0.PNG

```bash
python main.py "http://cdn.example.com/game.pkg" --icon
```

#### Apenas exibir o Content ID (sem extrair)

```bash
python main.py "http://cdn.example.com/game.pkg" --content-id
```

Saída:
```
Platform: PS3
Finalized: True
Content ID: UP0177-NPUB30443_00-SVCSONIC2XXXXXXX
Items: 16
Total: 35433776 bytes
Source: http://cdn.example.com/game.pkg
```

O PKG é aberto e as informações são exibidas, mas **nenhum arquivo é extraído**.

#### Extrair arquivo específico com `--path`

```bash
# Arquivo na raiz
python main.py "http://cdn.example.com/game.pkg" --path /ICON0.PNG

# Arquivo em subdiretório
python main.py "http://cdn.example.com/game.pkg" --path /USRDIR/0B/SONIC2.SR

# Caminho sem a barra inicial também funciona
python main.py "http://cdn.example.com/game.pkg" --path USRDIR/EBOOT.BIN
```

Se o caminho informado não existir dentro do PKG, o erro é exibido:
```
[ERRO] Falha na extracao: Arquivo "USRDIR/NAO_EXISTE.DAT" nao encontrado no PKG
```

#### Diretório de saída customizado

```bash
python main.py "http://cdn.example.com/game.pkg" --sfo -o minha_pasta
```

### Dica para Windows (Git Bash / MSYS2)

No Git Bash, caminhos que começam com `/` (ex: `--path /ICON0.PNG`) são convertidos automaticamente pelo shell para caminhos absolutos do Windows (ex: `C:\Program Files\Git\ICON0.PNG`).

O script detecta essa conversão e recupera o caminho original automaticamente. Você pode usar com segurança:

```bash
python main.py "http://cdn.example.com/game.pkg" --path /ICON0.PNG
```

---

## Construção de PKG customizado (`pkg_builder.py`)

Monta um arquivo `.pkg` assinado (non-finalized) a partir de uma estrutura de diretórios.

### Estrutura de entrada

O diretório de entrada (padrão: `custom/`) deve espelhar os caminhos absolutos do HDD do PS3:

```
custom/
├── dev_hdd0/
│   ├── game/
│   │   └── NPUB30443/
│   │       └── USRDIR/
│   │           └── EBOOT.BIN
│   └── home/
│       └── 00000001/
│           └── savedata/
└── dev_flash/
    └── vsh/
        └── resource/
            └── bg.rco
```

Os nomes dos arquivos recebem automaticamente o prefixo `../../` para criar paths absolutos no PKG.

### Uso

```bash
python pkg_builder.py               # usa ./custom/ como entrada
python pkg_builder.py minha_pasta   # diretório customizado
```

### Opções

| Flag | Descrição |
|------|-----------|
| `-o ARQUIVO` / `--output ARQUIVO` | Nome do `.pkg` de saída |
| `-c ID` / `--content-id ID` | Content ID (padrão: `CUSTOM-INSTALLER_00-0000000000000000`) |

### Exemplo

```bash
python pkg_builder.py -o meu_installer.pkg -c "UP0001-INSTALLER_00-0123456789ABCDEF"
```

Saída:
```
PKG criado: UP0001-INSTALLER_00-0123456789ABCDEF.pkg (123456 bytes)
Content ID: UP0001-INSTALLER_00-0123456789ABCDEF
```

---

## Aceleração C (`build_deps.py` / `pkgcrypt.c`)

Compila a extensão nativa `pkgcrypt` (SHA-1 + XOR em C) para acelerar a descriptografia de PKGs **non-finalized**.

```bash
python build_deps.py              # Compila
python build_deps.py --clean      # Remove binários compilados
```

A extensão é compilada para a plataforma atual com naming padronizado (`pkgcrypt.cpXY-<platform>.so` / `.pyd`) e é carregada automaticamente.

### Fallback

Se a extensão C não estiver disponível, a descriptografia em Python puro é usada como fallback.

---

## Como funciona

### Extração

1. **Leitura do cabeçalho** (offset `0x00`): magic `7F PKG`, revisão, tipo, Content ID, IV, digest
2. **Tabela de arquivos criptografada**: o offset da tabela está nos primeiros 16 bytes decriptados. Cada entrada tem 32 bytes: `name_offset \| name_size \| padding \| file_offset \| file_size \| flags`
3. **Descriptografia**:
   - **Finalized** (`revision == 0x8000`): AES-128-CTR com chave fixa do PS3/PSP e IV do cabeçalho
   - **Non-finalized**: cifra baseada em SHA-1 com o digest do cabeçalho (com fallback automático para o QA digest quando necessário)
4. **Extração**: itera sobre a tabela, descriptografa nomes e dados, e escreve os arquivos no disco

### Construção

1. **Varredura do diretório** de entrada para listar arquivos e diretórios
2. **Montagem do cabeçalho** com Content ID, offsets e placeholder para QA digest
3. **Cálculo do QA digest** (SHA-1 do cabeçalho + tabela de arquivos)
4. **Cálculo do KLicensee** (zeros encriptados com QA digest, contador `0xFFFFFFFFFFFFFFFF`)
5. **Bloco de metadados** com DRM type, content type, data size em float, etc.
6. **Criptografia**: SHA-1 + XOR de todo o bloco de dados com o QA digest
7. **Escrita**: cabeçalho → header SHA → padding duplamente encriptado → metadados → dados encriptados → padding final

## Licença

MIT
