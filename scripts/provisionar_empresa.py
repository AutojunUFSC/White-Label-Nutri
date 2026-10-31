#!/usr/bin/env python
"""Provisiona uma empresa nova, de forma interativa.

    python scripts/provisionar_empresa.py            # cria uma empresa
    python scripts/provisionar_empresa.py --rodar X  # sobe o servidor da empresa X
    python scripts/provisionar_empresa.py --remover X  # apaga a empresa X (banco + variaveis)

Cria o banco da empresa, gera as variaveis da instancia (SECRET_KEY propria), roda
`migrate` e `bootstrap_instancia`. As variaveis ficam em instancias/<slug>.env, fora
do Git. A senha do administrador nunca vai por argumento de linha de comando.

Modo local: nao configura Nginx, Gunicorn nem HTTPS (isso e etapa do servidor).
O servidor PostgreSQL e lido da DATABASE_URL do .env (so host, porta e credenciais;
o nome do banco e ignorado).
"""
import getpass
import os
import re
import secrets
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import environ
import psycopg
from psycopg import sql

RAIZ = Path(__file__).resolve().parent.parent
MANAGE = RAIZ / "backend" / "manage.py"
PASTA_INSTANCIAS = RAIZ / "instancias"

CORES = [
    ("Verde (padrao)", "#198754"), ("Azul", "#0d6efd"), ("Azul-marinho", "#0b3c8a"),
    ("Ciano", "#0891b2"), ("Roxo", "#6f42c1"), ("Indigo", "#4f46e5"),
    ("Rosa", "#d63384"), ("Vermelho", "#dc3545"), ("Laranja", "#e8590c"),
    ("Ambar", "#b45309"), ("Verde-escuro", "#166534"), ("Turquesa", "#0f766e"),
    ("Cinza-grafite", "#374151"), ("Marrom", "#7c4a2d"),
]


class Cancelado(Exception):
    pass


# ------------------------------------------------------------------ perguntas

def perguntar(texto, padrao=None, validar=None):
    sufixo = f" [{padrao}]" if padrao not in (None, "") else ""
    while True:
        resposta = input(f"{texto}{sufixo}: ").strip() or (padrao or "")
        if not resposta:
            print("  Campo obrigatorio.")
            continue
        erro = validar(resposta) if validar else None
        if erro:
            print(f"  {erro}")
            continue
        return resposta


def confirmar(texto, padrao=True):
    marca = "S/n" if padrao else "s/N"
    resposta = input(f"{texto} [{marca}]: ").strip().lower()
    return padrao if not resposta else resposta in ("s", "sim", "y", "yes")


def pedir_senha(texto):
    while True:
        senha = getpass.getpass(f"{texto}: ")
        if len(senha) < 8:
            print("  Use ao menos 8 caracteres.")
            continue
        if senha != getpass.getpass("Confirme a senha: "):
            print("  As senhas nao conferem.")
            continue
        return senha


def pedir_cor():
    print("Cores sugeridas:")
    for i, (nome, codigo) in enumerate(CORES, start=1):
        print(f"  {i:2}. {nome:<15} {codigo}")

    def validar(valor):
        if valor.isdigit():
            return None if 1 <= int(valor) <= len(CORES) else "Numero fora da lista."
        return None if re.fullmatch(r"#[0-9a-fA-F]{6}", valor) else "Use um numero da lista ou #RRGGBB."

    escolha = perguntar("Cor primaria (numero ou #RRGGBB)", "1", validar)
    return CORES[int(escolha) - 1][1] if escolha.isdigit() else escolha.lower()


def sugerir_slug(nome):
    ascii_ = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_.lower()).strip("_")
    return slug[:40] or "empresa"


def validar_slug(valor):
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,39}", valor):
        return "Use minusculas, numeros e _, comecando por letra (2 a 40 caracteres)."
    return None


def validar_email(valor):
    return None if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", valor) else "E-mail invalido."


def validar_ano(valor):
    return None if valor.isdigit() and (valor == "0" or 1990 <= int(valor) <= 2100) else "Use 0 ou um ano (ex.: 2024)."


# ------------------------------------------------------------------ servidor

def ler_servidor():
    """Host, porta e credenciais do PostgreSQL, a partir da DATABASE_URL do .env."""
    environ.Env.read_env(RAIZ / ".env")
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise Cancelado("DATABASE_URL nao encontrada. Defina-a no .env ou no ambiente.")
    partes = urlsplit(url)
    return {
        "host": partes.hostname or "localhost",
        "port": partes.port or 5432,
        "user": unquote(partes.username or "postgres"),
        "password": unquote(partes.password or ""),
    }


def conectar_manutencao(servidor):
    try:
        return psycopg.connect(dbname="postgres", autocommit=True, **servidor)
    except psycopg.OperationalError as erro:
        raise Cancelado(
            f"Nao consegui conectar ao PostgreSQL em {servidor['host']}:{servidor['port']} "
            f"como '{servidor['user']}'. Confira a DATABASE_URL do .env.\n  Detalhe: {erro}"
        )


def banco_existe(conexao, nome):
    return conexao.execute("SELECT 1 FROM pg_database WHERE datname = %s", (nome,)).fetchone() is not None


def url_do_banco(servidor, banco):
    return (
        f"postgres://{quote(servidor['user'], safe='')}:{quote(servidor['password'], safe='')}"
        f"@{servidor['host']}:{servidor['port']}/{banco}"
    )


# ------------------------------------------------------------------ execucao

def rodar_manage(ambiente, *argumentos):
    resultado = subprocess.run([sys.executable, str(MANAGE), *argumentos], env=ambiente, cwd=RAIZ)
    if resultado.returncode != 0:
        raise RuntimeError(f"'manage.py {argumentos[0]}' falhou (codigo {resultado.returncode}).")


def ler_env_instancia(slug):
    arquivo = PASTA_INSTANCIAS / f"{slug}.env"
    if not arquivo.exists():
        raise Cancelado(f"Nao existe {arquivo}. Empresas disponiveis: {listar_instancias() or 'nenhuma'}.")
    variaveis = {}
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        if linha.strip() and not linha.startswith("#") and "=" in linha:
            chave, _, valor = linha.partition("=")
            variaveis[chave.strip()] = valor.strip()
    return variaveis


def listar_instancias():
    if not PASTA_INSTANCIAS.exists():
        return ""
    return ", ".join(sorted(p.stem for p in PASTA_INSTANCIAS.glob("*.env")))


def localizar_pg_dump():
    achado = shutil.which("pg_dump")
    if achado:
        return achado
    candidatos = sorted(Path("C:/Program Files/PostgreSQL").glob("*/bin/pg_dump.exe"), reverse=True)
    return str(candidatos[0]) if candidatos else None


def contar_registros(servidor, banco):
    """Quantidade de membros, ingredientes e fichas; None se o banco nao responder."""
    tabelas = {"membros": "fichas_membro", "ingredientes": "fichas_ingrediente", "fichas": "fichas_ficha"}
    try:
        with psycopg.connect(dbname=banco, **servidor) as conexao:
            return {
                rotulo: conexao.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(tabela))).fetchone()[0]
                for rotulo, tabela in tabelas.items()
            }
    except psycopg.Error:
        return None


def fazer_backup(servidor, banco):
    pg_dump = localizar_pg_dump()
    if not pg_dump:
        raise Cancelado("pg_dump nao encontrado; sem backup nao apago. Nada foi removido.")
    destino = RAIZ / "backups" / f"{banco}_{datetime.now():%Y%m%d_%H%M%S}.dump"
    destino.parent.mkdir(exist_ok=True)
    resultado = subprocess.run(
        [pg_dump, "-Fc", "-h", servidor["host"], "-p", str(servidor["port"]),
         "-U", servidor["user"], "-f", str(destino), banco],
        env={**os.environ, "PGPASSWORD": servidor["password"]},
    )
    if resultado.returncode != 0:
        destino.unlink(missing_ok=True)
        raise Cancelado("O backup falhou; nada foi removido.")
    print(f"Backup salvo em {destino.relative_to(RAIZ)}")


def remover(slug):
    """Apaga uma empresa criada por este script: o banco e o arquivo de variaveis."""
    if validar_slug(slug):
        raise Cancelado(f"Identificador invalido: '{slug}'.")
    arquivo = PASTA_INSTANCIAS / f"{slug}.env"
    variaveis = ler_env_instancia(slug)  # recusa o que nao foi criado por este script
    banco = urlsplit(variaveis.get("DATABASE_URL", "")).path.lstrip("/")
    if banco != f"nutri_{slug}":
        raise Cancelado(f"O banco registrado ('{banco}') nao e 'nutri_{slug}'. Por seguranca, nao apago.")

    servidor = ler_servidor()
    conexao = conectar_manutencao(servidor)
    try:
        existe = banco_existe(conexao, banco)
        print(f"\n=== Remover empresa '{slug}' ===")
        print(f"  Banco:    {banco}" + ("" if existe else "  (nao existe mais no servidor)"))
        print(f"  Arquivo:  {arquivo.relative_to(RAIZ)}")
        if existe:
            totais = contar_registros(servidor, banco)
            if totais:
                print("  Dados:    " + ", ".join(f"{v} {k}" for k, v in totais.items()))
            print("\nIsto APAGA o banco e todos os dados dele, sem volta.")
            if confirmar("Fazer um backup antes?"):
                fazer_backup(servidor, banco)
        if input(f"\nPara confirmar, digite o identificador ({slug}): ").strip() != slug:
            raise Cancelado("Identificador diferente. Nada foi removido.")
        if existe:
            try:
                conexao.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(banco)))
            except psycopg.errors.ObjectInUse:
                raise Cancelado("O banco esta em uso. Pare o servidor dessa empresa (Ctrl+C) e tente de novo.")
            print(f"Banco '{banco}' apagado.")
        arquivo.unlink()
        print(f"Arquivo {arquivo.name} apagado.\nEmpresa '{slug}' removida.")
    finally:
        conexao.close()


def subir_servidor(slug, porta="8000"):
    ambiente = {**os.environ, **ler_env_instancia(slug)}
    print(f"\nSubindo '{slug}' em http://localhost:{porta}  (Ctrl+C para parar)\n")
    try:
        subprocess.run([sys.executable, str(MANAGE), "runserver", porta], env=ambiente, cwd=RAIZ)
    except KeyboardInterrupt:
        print("\nServidor encerrado.")


# ------------------------------------------------------------------ fluxo principal

def provisionar():
    print("=== Nova empresa ===\n")
    servidor = ler_servidor()
    print(f"Servidor PostgreSQL: {servidor['user']}@{servidor['host']}:{servidor['port']}\n")

    nome = perguntar("Nome da empresa")
    slug = perguntar("Identificador (slug)", sugerir_slug(nome), validar_slug)
    if (PASTA_INSTANCIAS / f"{slug}.env").exists():
        raise Cancelado(f"Ja existe uma empresa com o identificador '{slug}'.")
    banco = f"nutri_{slug}"
    dominio = perguntar("Dominio (use localhost para teste local)", "localhost")
    admin = perguntar("Usuario administrador", "admin")
    email = perguntar("E-mail do administrador", validar=validar_email)
    senha = pedir_senha("Senha do administrador")
    cor = pedir_cor()
    chave = perguntar("Chave de cadastro de membros", "CHAVE-" + secrets.token_hex(3).upper())
    ano_corte = perguntar("Ano de corte dos ingredientes (0 = sem corte)", "0", validar_ano)

    print("\n--- Resumo ---")
    print(f"  Empresa:        {nome}")
    print(f"  Banco:          {banco}")
    print(f"  Dominio:        {dominio}")
    print(f"  Administrador:  {admin} <{email}>")
    print(f"  Cor:            {cor}")
    print(f"  Chave:          {chave}")
    print(f"  Ano de corte:   {ano_corte}")
    if not confirmar("\nConfirma?", padrao=False):
        raise Cancelado("Nada foi criado.")

    conexao = conectar_manutencao(servidor)
    if banco_existe(conexao, banco):
        raise Cancelado(f"O banco '{banco}' ja existe neste servidor. Nada foi criado.")
    conexao.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(banco)))
    print(f"\n[1/4] Banco '{banco}' criado.")

    hosts = ["localhost", "127.0.0.1"] if dominio == "localhost" else [dominio, "localhost"]
    variaveis = {
        "DATABASE_URL": url_do_banco(servidor, banco),
        "SECRET_KEY": secrets.token_urlsafe(64),
        "ALLOWED_HOSTS": ",".join(hosts),
    }
    ambiente = {**os.environ, **variaveis, "INSTANCIA_ADMIN_SENHA": senha}
    try:
        print("[2/4] Aplicando migracoes...")
        rodar_manage(ambiente, "migrate", "--verbosity", "0")
        print("[3/4] Configurando a instancia...")
        rodar_manage(
            ambiente, "bootstrap_instancia", "--nome", nome, "--admin", admin,
            "--email", email, "--chave", chave, "--cor", cor, "--ano-corte", ano_corte,
        )
    except RuntimeError as erro:
        print(f"\nERRO: {erro}")
        if confirmar(f"Apagar o banco '{banco}' que acabei de criar?"):
            conexao.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(banco)))
            print("Banco apagado.")
        raise Cancelado("Provisionamento interrompido.")
    finally:
        conexao.close()

    PASTA_INSTANCIAS.mkdir(exist_ok=True)
    arquivo = PASTA_INSTANCIAS / f"{slug}.env"
    arquivo.write_text(
        "# Variaveis desta empresa. Contem segredos: nao versionar.\n"
        + "".join(f"{k}={v}\n" for k, v in variaveis.items()),
        encoding="utf-8",
    )
    print(f"[4/4] Variaveis salvas em {arquivo.relative_to(RAIZ)}")

    print("\n=== Empresa criada ===")
    print(f"  Empresa:        {nome}")
    print(f"  Administrador:  {admin}")
    print(f"  Chave:          {chave}   (cadastro em /registrarMembro)")
    print(f"  Para subir:     python scripts/provisionar_empresa.py --rodar {slug}")
    if confirmar("\nSubir o servidor agora?"):
        subir_servidor(slug)


def main():
    argumentos = sys.argv[1:]
    try:
        if argumentos[:1] == ["--rodar"]:
            if len(argumentos) != 2:
                raise Cancelado(f"Uso: --rodar <slug>. Disponiveis: {listar_instancias() or 'nenhuma'}.")
            subir_servidor(argumentos[1])
        elif argumentos[:1] == ["--remover"]:
            if len(argumentos) != 2:
                raise Cancelado(f"Uso: --remover <slug>. Disponiveis: {listar_instancias() or 'nenhuma'}.")
            remover(argumentos[1])
        elif argumentos:
            raise Cancelado("Uso: provisionar_empresa.py  |  --rodar <slug>  |  --remover <slug>")
        else:
            provisionar()
    except (Cancelado, KeyboardInterrupt) as erro:
        print(f"\n{erro}" if str(erro) else "\nCancelado.")
        sys.exit(1)


if __name__ == "__main__":
    main()
