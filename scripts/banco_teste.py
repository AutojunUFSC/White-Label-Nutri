#!/usr/bin/env python
"""Banco de teste local: uma empresa demo, com usuarios e ingredientes, sem perguntas.

    python scripts/banco_teste.py             # cria (se faltar) e sobe em http://localhost:8000
    python scripts/banco_teste.py --resetar   # apaga o banco demo e recria do zero
    python scripts/banco_teste.py --sem-servidor

Usa o PostgreSQL da DATABASE_URL do .env e cria o banco `nutri_demo` (variaveis em
instancias/demo.env, fora do Git). Login: admin / nutri / aluno, senha `demo1234`.
"""
import os
import secrets
import sys

from psycopg import sql

from provisionar_empresa import (
    PASTA_INSTANCIAS, RAIZ, Cancelado, banco_existe, conectar_manutencao,
    ler_env_instancia, ler_servidor, rodar_manage, subir_servidor, url_do_banco,
)

SLUG = "demo"
BANCO = f"nutri_{SLUG}"


def preparar(resetar):
    servidor = ler_servidor()
    arquivo = PASTA_INSTANCIAS / f"{SLUG}.env"
    conexao = conectar_manutencao(servidor)
    try:
        if resetar and banco_existe(conexao, BANCO):
            try:
                conexao.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(BANCO)))
            except Exception as erro:
                raise Cancelado(f"Nao consegui apagar '{BANCO}' (servidor rodando?): {erro}")
            print(f"Banco '{BANCO}' apagado.")
        if not banco_existe(conexao, BANCO):
            conexao.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(BANCO)))
            print(f"Banco '{BANCO}' criado.")
    finally:
        conexao.close()

    if not arquivo.exists():
        PASTA_INSTANCIAS.mkdir(exist_ok=True)
        variaveis = {
            "DATABASE_URL": url_do_banco(servidor, BANCO),
            "SECRET_KEY": secrets.token_urlsafe(64),
            "ALLOWED_HOSTS": "localhost,127.0.0.1",
            "DEBUG": "True",
        }
        arquivo.write_text(
            "# Banco de teste local. Nao versionar.\n"
            + "".join(f"{k}={v}\n" for k, v in variaveis.items()),
            encoding="utf-8",
        )
    ambiente = {**os.environ, **ler_env_instancia(SLUG)}
    rodar_manage(ambiente, "migrate", "--verbosity", "0")
    rodar_manage(ambiente, "seed_demo")


def main():
    argumentos = set(sys.argv[1:])
    desconhecidos = argumentos - {"--resetar", "--sem-servidor"}
    try:
        if desconhecidos:
            raise Cancelado("Uso: banco_teste.py [--resetar] [--sem-servidor]")
        preparar("--resetar" in argumentos)
        if "--sem-servidor" not in argumentos:
            subir_servidor(SLUG)
    except (Cancelado, RuntimeError, KeyboardInterrupt) as erro:
        print(f"\n{erro}" if str(erro) else "\nCancelado.")
        sys.exit(1)


if __name__ == "__main__":
    main()
