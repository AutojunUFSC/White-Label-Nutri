"""Tour de boas-vindas: aparece no primeiro acesso de cada usuário e sob demanda na Ajuda."""
import pytest
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils import timezone

from apps.fichas.models import Membro
from apps.plataforma.models import ConfiguracaoInstancia

SENHA = "s3nh4-forte"


def criar_membro(username="laura", superusuario=False, ja_entrou=False):
    user = User.objects.create_user(username, password=SENHA, is_superuser=superusuario)
    if ja_entrou:
        user.last_login = timezone.now()
        user.save()
    Membro.objects.create(usuario=user, nome=username, semestre="2024.1", email=f"{username}@x.com")
    return user


def entrar(client, username="laura"):
    return client.post("/loginUser", {"username": username, "password": SENHA})


def lista(client):
    return client.get("/listaFichas").content.decode()


def test_primeiro_acesso_abre_o_tour(client, db):
    criar_membro()
    entrar(client)
    corpo = lista(client)
    assert 'id="tourModal"' in corpo
    assert 'data-tour-automatico="true"' in corpo
    assert "js/tour.js" in corpo


def test_tour_abre_uma_unica_vez_na_sessao(client, db):
    criar_membro()
    entrar(client)
    assert 'id="tourModal"' in lista(client)
    assert 'id="tourModal"' not in lista(client)


def test_segundo_login_nao_abre_o_tour(client, db):
    criar_membro()
    entrar(client)
    lista(client)
    client.get("/logoutUser")
    entrar(client)
    assert 'id="tourModal"' not in lista(client)


def test_usuario_que_ja_usava_o_sistema_nao_ve_o_tour(client, db):
    criar_membro(ja_entrou=True)
    entrar(client)
    assert 'id="tourModal"' not in lista(client)


def test_ajuda_tem_botao_para_rever_sem_abrir_sozinho(client, db):
    user = criar_membro(ja_entrou=True)
    client.force_login(user)
    corpo = client.get("/ajuda").content.decode()
    assert 'id="tourModal"' in corpo
    assert 'data-tour-automatico="false"' in corpo
    assert "data-tour-abrir" in corpo


def test_ajuda_nao_duplica_o_tour_no_primeiro_acesso(client, db):
    criar_membro()
    entrar(client)
    corpo = client.get("/ajuda").content.decode()
    assert corpo.count('id="tourModal"') == 1
    assert 'data-tour-automatico="true"' in corpo


def test_tour_usa_o_nome_da_empresa(client, db):
    ConfiguracaoInstancia.objects.create(nome_exibicao="Empresa Exemplo")
    criar_membro()
    entrar(client)
    assert "Bem-vindo(a) ao Empresa Exemplo" in lista(client)


def test_passo_de_membros_so_aparece_para_administrador(client, db):
    criar_membro("comum")
    entrar(client, "comum")
    assert 'data-tour-passo="membros"' not in lista(client)
    client.get("/logoutUser")

    criar_membro("gestora", superusuario=True)
    entrar(client, "gestora")
    assert 'data-tour-passo="membros"' in lista(client)


def test_tela_de_login_nao_carrega_o_tour(client, db):
    assert 'id="tourModal"' not in client.get("/loginUser").content.decode()


def test_texto_do_tour_e_generico():
    html = render_to_string("_tour.html", {"instancia_nome": "Qualquer Empresa", "tour_administrador": True})
    for nome_de_cliente in ("nutri jr", "nutrijr", "acme"):
        assert nome_de_cliente not in html.lower()
