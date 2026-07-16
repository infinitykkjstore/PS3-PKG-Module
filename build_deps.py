#!/usr/bin/env python3
"""
build_deps.py - Compila a extensao C pkgcrypt para aceleracao de criptografia.

Uso:
    python build_deps.py              # Compila para a plataforma atual
    python build_deps.py --clean      # Remove binarios compilados
"""
import os, sys, shutil, platform, struct

HERE = os.path.dirname(os.path.abspath(__file__))
C_SRC = os.path.join(HERE, "pkgcrypt.c")
BUILD_DIR = os.path.join(HERE, "build")

def get_platform_tag():
    machine = platform.machine().lower()
    bits = struct.calcsize("P") * 8
    system = platform.system().lower()

    if system == "windows":
        if machine in ("amd64", "x86_64"):
            return "win-amd64"
        return "win-arm64" if "arm" in machine or "aarch" in machine else "win32"
    elif system == "linux":
        if machine in ("x86_64", "amd64"):
            return "linux-x86_64"
        elif machine in ("aarch64", "arm64"):
            return "linux-aarch64"
        elif machine.startswith("arm"):
            return "linux-armv7l"
        return "linux-" + machine
    elif system == "darwin":
        if machine in ("arm64", "aarch64"):
            return "macosx-arm64"
        return "macosx-x86_64"
    return f"{system}-{machine}"

def get_python_tag():
    return f"cp{sys.version_info.major}{sys.version_info.minor}"

def get_ext_suffix():
    if sys.platform == "win32":
        return ".pyd"
    return ".so"

def get_soname(plat_tag):
    ext = ".pyd" if plat_tag.startswith("win") else ".so"
    return f"pkgcrypt.{get_python_tag()}-{plat_tag}{ext}"

def try_compile():
    print(f"[build_deps] Platforma: {sys.platform}")
    print(f"[build_deps] Python: {sys.version}")

    if not os.path.isfile(C_SRC):
        print(f"[ERRO] {C_SRC} nao encontrado")
        return False

    try:
        from setuptools import setup, Extension
    except ImportError:
        print("[build_deps] setuptools nao disponivel, tentando distutils...")
        try:
            from distutils.core import setup, Extension
        except ImportError:
            print("[ERRO] setuptools/distutils nao encontrados. Instale setuptools.")
            return False

    libs = []
    extra_args = {}

    plat_tag = get_platform_tag()
    so_name = get_soname(plat_tag)
    so_path = os.path.join(HERE, so_name)

    build_dir = os.path.join(HERE, "build_temp")
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)

    print(f"[build_deps] Compilando pkgcrypt.c -> {so_name} ...")

    ext = Extension(
        "pkgcrypt",
        sources=[C_SRC],
        libraries=libs,
        **extra_args
    )

    try:
        setup(
            name="pkgcrypt",
            ext_modules=[ext],
            script_args=["build_ext", "--build-temp", build_dir, "--build-lib", HERE, "--inplace"],
        )
    except SystemExit as e:
        if e.code != 0:
            print(f"[build_deps] Falha na compilacao (codigo {e.code})")
            if os.path.isdir(build_dir):
                shutil.rmtree(build_dir)
            return False

    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)

    so_name = None
    for f in os.listdir(HERE):
        if f.startswith("pkgcrypt.") and (f.endswith(".so") or f.endswith(".pyd")):
            if f != "pkgcrypt.c":
                so_name = f
                break

    if so_name:
        print(f"[build_deps] OK: {so_name}")
        return True
    else:
        print("[build_deps] .so/.pyd nao encontrado apos compilacao")
        return False

def clean():
    for f in os.listdir(HERE):
        if f.startswith("pkgcrypt.") and (f.endswith(".so") or f.endswith(".pyd")):
            os.remove(os.path.join(HERE, f))
            print(f"  removido {f}")
    build_dirs = [os.path.join(HERE, "build"), os.path.join(HERE, "build_temp")]
    for d in build_dirs:
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"  removido {d}/")
    print("[build_deps] Limpeza concluida")

def main():
    if "--clean" in sys.argv:
        clean()
        return

    ok = try_compile()
    if not ok:
        print()
        print("Para compilar manualmente:")
        print(f"  cd {HERE}")
        print("  python -c \"from setuptools import setup, Extension;")
        print("  setup(name='pkgcrypt', ext_modules=[Extension('pkgcrypt', sources=['pkgcrypt.c'])])")
        sys.exit(1)
    print()
    print("Extensao C compilada com sucesso! A aceleracao estara ativa na proxima execucao.")

if __name__ == "__main__":
    main()
