"""Provisiona uma instância nova (nova empresa cliente — D-009).

Cada empresa roda com banco e hospedagem próprios; este comando prepara um banco
recém-migrado: configuração white-label, grupo de administradores, primeiro
usuário administrador e chave de cadastro.

    python manage.py bootstrap_instancia --nome "SUA-EMPRESA" \
        --admin admin --email admin@sua-empresa.com --chave SUA-CHAVE-2026

A senha pode vir por --senha ou pela variável de ambiente INSTANCIA_ADMIN_SENHA;
sem nenhuma das duas, é solicitada interativamente.
"""
import getpass
import os

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.fichas.models import Chave, Membro
from apps.plataforma.models import ConfiguracaoInstancia


class Command(BaseCommand):
    help = "Configura uma instância nova (empresa cliente) em um banco já migrado."

    def add_arguments(self, parser):
        parser.add_argument("--nome", required=True, help="Nome de exibição da empresa.")
        parser.add_argument("--admin", required=True, help="Usuário administrador inicial.")
        parser.add_argument("--email", default="", help="E-mail do administrador.")
        parser.add_argument("--senha", default=None, help="Senha do administrador.")
        parser.add_argument("--chave", required=True, help="Chave de cadastro de membros.")
        parser.add_argument(
            "--cor", default="#198754", help="Cor primária em hex (default: #198754)."
        )
        parser.add_argument(
            "--ano-corte",
            type=int,
            default=0,
            help="Ano de corte dos ingredientes (0 = sem corte, padrão para empresas novas).",
        )

    def handle(self, *args, **opcoes):
        if ConfiguracaoInstancia.objects.exists():
            raise CommandError(
                "Esta instância já está configurada. Para alterar dados, use o admin "
                "do Django (Configuração da instância)."
            )
        if User.objects.filter(username=opcoes["admin"]).exists():
            raise CommandError(f"O usuário '{opcoes['admin']}' já existe neste banco.")

        senha = opcoes["senha"] or os.environ.get("INSTANCIA_ADMIN_SENHA")
        if not senha:
            senha = getpass.getpass("Senha do administrador: ")
            if senha != getpass.getpass("Confirme a senha: "):
                raise CommandError("As senhas não conferem.")
        if not senha:
            raise CommandError("A senha do administrador é obrigatória.")

        with transaction.atomic():
            ConfiguracaoInstancia.objects.create(
                nome_exibicao=opcoes["nome"],
                cor_primaria=opcoes["cor"],
                ano_corte_ingredientes=opcoes["ano_corte"] or None,
            )
            usuario = User.objects.create_user(
                opcoes["admin"], email=opcoes["email"], password=senha
            )
            # Superusuário: o grupo não tem permissões de modelo, e sem elas o admin
            # (onde se ajustam nome, cor e logotipo) abriria vazio para este usuário.
            usuario.is_staff = True
            usuario.is_superuser = True
            usuario.save()
            grupo, _ = Group.objects.get_or_create(name=settings.GRUPO_ADMINISTRADORES)
            usuario.groups.add(grupo)
            Membro.objects.create(
                usuario=usuario,
                nome=opcoes["admin"],
                semestre="",
                email=opcoes["email"],
            )
            Chave.objects.create(key=opcoes["chave"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Instância '{opcoes['nome']}' configurada.\n"
                f"  Administrador: {opcoes['admin']}\n"
                f"  Chave de cadastro: {opcoes['chave']}\n"
                "Novos membros se cadastram em /registrarMembro com essa chave."
            )
        )
