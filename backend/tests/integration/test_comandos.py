"""Testes do comando de provisionamento de instância (E6)."""
from io import StringIO

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command

from apps.fichas.models import Chave, Membro
from apps.plataforma.models import ConfiguracaoInstancia


def executar(comando, *args, **kwargs):
    saida = StringIO()
    call_command(comando, *args, stdout=saida, stderr=saida, **kwargs)
    return saida.getvalue()


@pytest.fixture
def membro(db):
    user = User.objects.create_user("admin", password="s3nh4-forte")
    return Membro.objects.create(usuario=user, nome="Admin", semestre="", email="a@x.com")


# -------------------------------------------------------- bootstrap_instancia


def test_bootstrap_configura_empresa_nova(db):
    saida = executar(
        "bootstrap_instancia",
        "--nome", "Nutri Acme",
        "--admin", "ana",
        "--email", "ana@acme.com",
        "--senha", "S3nh4-Long4!",
        "--chave", "ACME-2026",
        "--cor", "#aa00aa",
    )
    assert "configurada" in saida

    config = ConfiguracaoInstancia.atual()
    assert config.nome_exibicao == "Nutri Acme"
    assert config.cor_primaria == "#aa00aa"
    assert config.ano_corte_ingredientes is None  # empresas novas sem corte (D-010)

    usuario = User.objects.get(username="ana")
    assert usuario.check_password("S3nh4-Long4!")
    assert usuario.groups.filter(name=settings.GRUPO_ADMINISTRADORES).exists()
    assert Membro.objects.filter(usuario=usuario).exists()
    assert Chave.objects.last().key == "ACME-2026"


def test_bootstrap_recusa_instancia_ja_configurada(db):
    ConfiguracaoInstancia.objects.create(nome_exibicao="Existente")
    with pytest.raises(CommandError, match="já está configurada"):
        executar(
            "bootstrap_instancia", "--nome", "Outra", "--admin", "x",
            "--senha", "S3nh4-Long4!", "--chave", "K",
        )


def test_bootstrap_recusa_usuario_existente(db, membro):
    with pytest.raises(CommandError, match="já existe"):
        executar(
            "bootstrap_instancia", "--nome", "Nova", "--admin", "admin",
            "--senha", "S3nh4-Long4!", "--chave", "K",
        )


def test_empresa_nova_funciona_ponta_a_ponta(client, db):
    """Cenário de venda: provisionar, cadastrar membro com a chave e entrar."""
    executar(
        "bootstrap_instancia",
        "--nome", "Nutri Beta", "--admin", "gestor",
        "--senha", "S3nh4-Long4!", "--chave", "BETA-1",
    )
    resp = client.post(
        "/registrarMembro",
        {
            "nome": "nutricionista", "semestre": "2026.1", "email": "n@beta.com",
            "senha1": "Outr4-S3nh4!", "senha2": "Outr4-S3nh4!", "chave": "BETA-1",
        },
    )
    assert resp.status_code == 302
    assert client.post(
        "/loginUser", {"username": "nutricionista", "password": "Outr4-S3nh4!"}
    ).url == "/listaFichas"
    # branding da instância aparece na interface
    assert "Nutri Beta" in client.get("/listaFichas").content.decode()


def test_testar_leitura_rotulo_grava_csv(tmp_path, settings, monkeypatch):
    import io

    from django.core.management import call_command
    from PIL import Image

    from apps.fichas import leitura_rotulo

    settings.GEMINI_API_KEY = "chave-de-teste"
    monkeypatch.setattr(
        leitura_rotulo, "_chamar_gemini",
        lambda jpeg: '{"e_tabela_nutricional": true, "nutrientes": '
                     '{"proteinas": {"por_100g": 7}}}',
    )
    Image.new("RGB", (100, 100)).save(tmp_path / "a.jpg")
    saida = tmp_path / "saida.csv"
    call_command("testar_leitura_rotulo", str(tmp_path), saida=str(saida), stdout=io.StringIO())
    conteudo = saida.read_text(encoding="utf-8-sig")
    assert "a.jpg" in conteudo and ";7" in conteudo
