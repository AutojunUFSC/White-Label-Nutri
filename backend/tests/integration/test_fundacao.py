"""Testes da E1: autenticação, listagem e configuração de instância."""
import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from apps.fichas.models import Ficha, Membro
from apps.plataforma.models import ConfiguracaoInstancia


@pytest.fixture
def membro(db):
    user = User.objects.create_user("laura", password="s3nh4-forte")
    return Membro.objects.create(usuario=user, nome="Laura", semestre="2024.1", email="l@x.com")


def test_login_com_credenciais_validas(client, membro):
    resp = client.post("/loginUser", {"username": "laura", "password": "s3nh4-forte"})
    assert resp.status_code == 302
    assert resp.url == "/listaFichas"


def test_login_invalido_mostra_mensagem(client, db):
    resp = client.post("/loginUser", {"username": "x", "password": "errada"})
    assert resp.status_code == 200
    assert "Não foi possível fazer login" in resp.content.decode()


def test_lista_fichas_exige_login(client, db):
    resp = client.get("/listaFichas")
    assert resp.status_code == 302
    assert "/loginUser" in resp.url


def test_lista_fichas_ordena_por_data_desc(client, membro):
    Ficha.objects.create(autor=membro, cliente="A", nomeFicha="Antiga", dataCriacao="2020-01-01")
    Ficha.objects.create(autor=membro, cliente="B", nomeFicha="Recente", dataCriacao="2025-01-01")
    client.force_login(membro.usuario)
    corpo = client.get("/listaFichas").content.decode()
    assert corpo.index("Recente") < corpo.index("Antiga")


def test_filtro_por_contains(client, membro):
    Ficha.objects.create(autor=membro, cliente="Padaria", nomeFicha="Pão vegano", dataCriacao="2025-01-01")
    Ficha.objects.create(autor=membro, cliente="Outra", nomeFicha="Bolo", dataCriacao="2025-01-02")
    client.force_login(membro.usuario)
    corpo = client.get("/listaFichas", {"f_nomeFicha": "Pão", "f_cliente": "", "f_autor": ""}).content.decode()
    assert "Pão vegano" in corpo and "Bolo" not in corpo


def test_configuracao_instancia_e_singleton(db):
    ConfiguracaoInstancia.objects.create(nome_exibicao="Empresa 1")
    segunda = ConfiguracaoInstancia(nome_exibicao="Empresa 2")
    with pytest.raises(ValidationError):
        segunda.full_clean()


def test_branding_aparece_no_login(client, db):
    ConfiguracaoInstancia.objects.create(nome_exibicao="EmpresaTeste", cor_primaria="#aa00aa")
    corpo = client.get("/loginUser").content.decode()
    assert "EmpresaTeste" in corpo and "#aa00aa" in corpo
