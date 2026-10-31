"""Tour de boas-vindas guiado: começa no primeiro acesso e sob demanda na Ajuda."""
import json
import re

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from apps.fichas.models import Membro
from apps.fichas.tour import passos
from apps.plataforma.models import ConfiguracaoInstancia

SENHA = "s3nh4-forte"
DADOS = re.compile(r'<script id="tour-dados" type="application/json">(.*?)</script>', re.S)


def criar_membro(username="laura", superusuario=False, ja_entrou=False):
    user = User.objects.create_user(username, password=SENHA, is_superuser=superusuario)
    if ja_entrou:
        user.last_login = timezone.now()
        user.save()
    Membro.objects.create(usuario=user, nome=username, semestre="2024.1", email=f"{username}@x.com")
    return user


def entrar(client, username="laura"):
    return client.post("/loginUser", {"username": username, "password": SENHA})


def pagina(client, url="/listaFichas"):
    return client.get(url).content.decode()


def dados_do_tour(corpo):
    achado = DADOS.search(corpo)
    return json.loads(achado.group(1)) if achado else None


def test_primeiro_acesso_entrega_o_roteiro_e_comeca_sozinho(client, db):
    criar_membro()
    entrar(client)
    corpo = pagina(client)
    dados = dados_do_tour(corpo)
    assert dados["automatico"] is True
    assert dados["inicio"] == "/listaFichas"
    assert dados["passos"][0]["id"] == "boas-vindas"
    assert "js/tour.js" in corpo


def test_tour_comeca_uma_unica_vez_na_sessao(client, db):
    criar_membro()
    entrar(client)
    assert dados_do_tour(pagina(client)) is not None
    assert dados_do_tour(pagina(client)) is None


def test_segundo_login_nao_comeca_o_tour(client, db):
    criar_membro()
    entrar(client)
    pagina(client)
    client.get("/logoutUser")
    entrar(client)
    assert dados_do_tour(pagina(client)) is None


def test_usuario_que_ja_usava_o_sistema_nao_ve_o_tour(client, db):
    criar_membro(ja_entrou=True)
    entrar(client)
    assert dados_do_tour(pagina(client)) is None


def test_ajuda_oferece_rever_o_tour_sem_comecar_sozinho(client, db):
    client.force_login(criar_membro(ja_entrou=True))
    corpo = pagina(client, "/ajuda")
    assert dados_do_tour(corpo)["automatico"] is False
    assert "data-tour-abrir" in corpo


def test_ajuda_no_primeiro_acesso_nao_duplica_os_dados(client, db):
    criar_membro()
    entrar(client)
    corpo = pagina(client, "/ajuda")
    assert corpo.count('id="tour-dados"') == 1
    assert dados_do_tour(corpo)["automatico"] is True


def test_script_carrega_nas_telas_logadas_para_retomar_o_passeio(client, db):
    client.force_login(criar_membro(ja_entrou=True))
    corpo = pagina(client, "/listaIngredientes")
    assert "js/tour.js" in corpo
    assert dados_do_tour(corpo) is None
    assert 'data-rota="listaIngredientes"' in corpo


def test_tela_de_login_nao_carrega_o_tour(client, db):
    corpo = pagina(client, "/loginUser")
    assert "js/tour.js" not in corpo and dados_do_tour(corpo) is None


def test_boas_vindas_usa_o_nome_da_empresa(client, db):
    ConfiguracaoInstancia.objects.create(nome_exibicao="Empresa Exemplo")
    criar_membro()
    entrar(client)
    assert dados_do_tour(pagina(client))["passos"][0]["titulo"] == "Bem-vindo(a) ao Empresa Exemplo"


def test_passo_de_membros_so_para_administrador(client, db):
    criar_membro("comum")
    entrar(client, "comum")
    ids = [p["id"] for p in dados_do_tour(pagina(client))["passos"]]
    assert "membros" not in ids
    client.get("/logoutUser")

    criar_membro("gestora", superusuario=True)
    entrar(client, "gestora")
    ids = [p["id"] for p in dados_do_tour(pagina(client))["passos"]]
    assert "membros" in ids


def test_todo_alvo_do_roteiro_existe_na_tela_do_passo(client, db):
    """Se alguém tirar um data-tour de um template, o passo apontaria para o vazio."""
    client.force_login(criar_membro("gestora", superusuario=True, ja_entrou=True))
    for passo in passos("Empresa", administrador=True):
        if passo["alvo"] is None:
            continue
        atributo = passo["alvo"].replace("[", "").replace("]", "")  # data-tour="x"
        corpo = pagina(client, reverse(passo["rota"]))
        assert atributo in corpo, f"{passo['id']}: {atributo} não existe em {passo['rota']}"


def test_passos_clicar_apontam_para_links_do_roteiro_seguinte(db):
    """Um passo 'clicar' leva à tela do passo seguinte, senão o tour se encerraria."""
    roteiro = passos("Empresa", administrador=True)
    destino = {
        "ingredientes": "listaIngredientes",
        "fichas": "listaFichas",
        "nova-ficha": "registrarFicha1",
    }
    for atual, seguinte in zip(roteiro, roteiro[1:]):
        if atual["acao"] == "clicar":
            assert seguinte["rota"] == destino[atual["id"]]


def test_roteiro_e_generico():
    texto = json.dumps(passos("Qualquer Empresa", administrador=True), ensure_ascii=False).lower()
    for nome_de_cliente in ("nutri jr", "nutrijr", "acme"):
        assert nome_de_cliente not in texto
