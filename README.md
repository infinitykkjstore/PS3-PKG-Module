# PS3-PKG-Module

Extrai e cria arquivos `.pkg` do PS3 (e PSP).

```bash
pip install pycryptodome       # opcional, necessario para PKGs finalized
python build_deps.py            # opcional, acelera extracao de PKGs non-finalized
```

---

## Extração (`main.py`)

Extrai PKGs de URL ou arquivo local.

```bash
python main.py "http://site.com/game.pkg"                # de URL
python main.py Sonic_the_Hedgehog_2.pkg                  # de arquivo local
python main.py Sonic_the_Hedgehog_2.pkg --sfo            # extrai apenas PARAM.SFO
python main.py Sonic_the_Hedgehog_2.pkg --content-id     # so mostra o Content ID
python main.py Sonic_the_Hedgehog_2.pkg -o minha_pasta   # diretorio de saida
```

| Flag | Descrição |
|------|-----------|
| (nenhuma) | Extrai **todos** os arquivos (padrão) |
| `--sfo` | Extrai apenas `PARAM.SFO` |
| `--eboot` | Extrai apenas `EBOOT.BIN` |
| `--pic1` / `--pic0` / `--icon` | Extrai a imagem correspondente |
| `--path CAMINHO` | Extrai um arquivo específico (ex: `--path /USRDIR/EBOOT.BIN`) |
| `--content-id` | Exibe o Content ID e sai (não extrai nada) |
| `-o DIR` | Diretório de saída (padrão: `PS3/`) |

---

## Construção de PKG (`pkg_builder.py`)

Monta um `.pkg` a partir de um diretório. Dois modos:

| Modo | Uso |
|------|-----|
| **custom** (padrão) | Paths com prefixo `../../` para CFW |
| **retail** (`--retail`) | Paths relativos (ex: `USRDIR/EBOOT.BIN`) |

### Modo custom

O diretório espelha o HDD do PS3. Os paths recebem prefixo `../../` automaticamente.

```
custom/
└── dev_hdd0/
    └── game/
        └── NPUB30443/
            ├── USRDIR/EBOOT.BIN
            └── PARAM.SFO
```

```bash
python pkg_builder.py                         # usa ./custom/
python pkg_builder.py minha_pasta/            # diretorio customizado
```

### Modo retail

O diretório contém a estrutura extraída pelo `main.py`. Content type é detectado automaticamente (GameExec se `USRDIR/EBOOT.BIN` existir, senão GameData).

```
extracao/
├── PARAM.SFO
├── ICON0.PNG
├── USRDIR/
│   └── EBOOT.BIN
└── TROPDIR/NPWR00001_00/TROPHY.TRP
```

```bash
python pkg_builder.py extracao/ --retail -c "UP0177-NPUB30443_00-SVCSONIC2XXXXXXX"
python pkg_builder.py extracao/ --retail -c "UP0177-NPUB30443_00-SVCSONIC2XXXXXXX" --rap game.rap
```

### Opções

| Flag | Descrição |
|------|-----------|
| `--retail` | Modo retail (sem prefixo `../../`) |
| `--rap ARQUIVO.rap` | Arquivo `.rap` de licença (16 bytes) |
| `-o ARQUIVO` | Nome do `.pkg` de saída |
| `-c ID` | Content ID |

### Exemplos

```bash
# Custom
python pkg_builder.py -o meu_installer.pkg

# Retail
python pkg_builder.py extracao/ --retail -c "UP0177-NPUB30443_00-SVCSONIC2XXXXXXX"

# Retail com RAP
python pkg_builder.py extracao/ --retail -c "UP0177-NPUB30443_00-SVCSONIC2XXXXXXX" --rap game.rap -o saida.pkg
```

Saída:
```
PKG criado: saida.pkg (35433712 bytes)
Content ID: UP0177-NPUB30443_00-SVCSONIC2XXXXXXX
Modo: retail
RAP copiado: saida.rap
```

---

## Aceleração C (`build_deps.py`)

Compila a extensão nativa para acelerar a descriptografia de PKGs non-finalized.

```bash
python build_deps.py              # compila
python build_deps.py --clean      # remove binarios compilados
```

Se a extensão C não estiver disponível, o fallback em Python puro é usado automaticamente.

---

## Licença

MIT
