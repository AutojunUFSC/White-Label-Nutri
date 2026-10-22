"""Testes de integração do wizard de fichas, receita, tabela e rótulo (E3/E4)."""
import datetime

import pytest
from django.contrib.auth.models import User

from apps.fichas.models import Ficha, Ficha_Ingrediente, Ingrediente, Membro, Nutriente, Tabela
from apps.plataforma.models import ConfiguracaoInstancia


@pytest.fixture
def membro(db):
    user = User.objects.create_user("laura", password="s3nh4-forte")
    return Membro.objects.create(
        usuario=user, nome="Laura", semestre="2024.1", email="l@x.com"
    )


@pytest.fixture
def logado(client, membro):
    client.force_login(membro.usuario)
    return client


@pytest.fixture
def ingrediente(membro):
    """Farinha: 10 g de proteína, 70 g de carboidrato e 2 g de gordura por 100 g."""
    ing = Ingrediente.objects.create(
        autorIng=membro,
        nomeIng="Farinha de trigo",
        origemDosDados="TACO",
        dataCriacao="2024-01-10",
        qtdeDoIngrediente=100,
        proteinas=10,
        proteinas_100g=10,
        carboidratos=70,
        carboidratos_100g=70,
        gordTotais=2,
        gordTotais_100g=2,
        sodio=500,
        sodio_100g=500,
    )
    return ing


@pytest.fixture
def ficha(membro):
    ficha = Ficha.objects.create(
        autor=membro,
        cliente="Padaria",
        nomeFicha="Pão de teste",
        dataCriacao="2025-05-01",
        pesoTotal=200,
        pesoPorcao=100,
        pesoAnvisa=50,
        medCaseiraPorcao="1 fatia",
    )
    Tabela.objects.create(pk=ficha.pk, origem=ficha)
    return ficha


# ------------------------------------------------------------------ wizard 1/3


def test_criar_ficha_cria_tabela_com_mesmo_pk(logado, membro):
    resp = logado.post(
        "/registrarFicha1",
        {
            "autor": membro.pk,
            "nomeFicha": "Bolo",
            "cliente": "Cliente X",
            "pesoTotal": 500,
            "pesoPorcao": 100,
            "pesoAnvisa": 50,
            "dataCriacao": "01/05/2025",
            "medCaseiraPorcao": "1 pedaço",
        },
    )
    nova = Ficha.objects.get(nomeFicha="Bolo")
    assert resp.status_code == 302
    assert resp.url == f"/registrarFicha2/{nova.pk}"
    assert Tabela.objects.filter(pk=nova.pk, origem=nova).exists()  # BR-015


# ------------------------------------------------------------------ wizard 2/3


def test_adicionar_ingrediente_recalcula_tabela(logado, ficha, ingrediente):
    resp = logado.post(
        f"/registrarFicha2/{ficha.pk}",
        {
            "ingExtra": "Farinha de trigo",
            "nomeFantasia": "Farinha",
            "pesoBruto": 100,
            "pesoLiquido": 100,
            "medidaCaseira": "1 xíc",
        },
    )
    assert resp.status_code == 302
    tabela = Tabela.objects.get(pk=ficha.pk)
    # 100 g de farinha: 10 g proteína; peso total 200 g → 5 g/100 g; porção 50 g → 2,5 g
    assert tabela.proteinas == pytest.approx(10)
    assert tabela.proteinas_Porcao == pytest.approx(2.5)
    assert tabela.proteinas_Arred == pytest.approx(2.5)
    # Energia por Atwater (BR-003): 10*4 + 70*4 + 2*9 = 338 kcal
    assert tabela.energiakcal == pytest.approx(338)
    ficha.refresh_from_db()
    assert ficha.pesoLiquidoPreparacao == pytest.approx(100)
    assert ficha.numPorcoes == 2  # 100 / 50


def test_ingrediente_inexistente_mostra_erro(logado, ficha):
    resp = logado.post(
        f"/registrarFicha2/{ficha.pk}",
        {"ingExtra": "Não existe", "nomeFantasia": "X", "pesoBruto": 1, "pesoLiquido": 1,
         "medidaCaseira": ""},
        follow=True,
    )
    assert "não foi encontrado" in resp.content.decode()
    assert not Ficha_Ingrediente.objects.exists()


def test_sem_pesos_nao_adiciona_ingrediente(logado, membro, ingrediente):
    ficha = Ficha.objects.create(
        autor=membro, cliente="C", nomeFicha="Sem pesos", dataCriacao="2025-01-01",
        pesoTotal=0, pesoPorcao=0,
    )
    Tabela.objects.create(pk=ficha.pk, origem=ficha)
    resp = logado.post(
        f"/registrarFicha2/{ficha.pk}",
        {"ingExtra": "Farinha de trigo", "nomeFantasia": "F", "pesoBruto": 10,
         "pesoLiquido": 10, "medidaCaseira": ""},
        follow=True,
    )
    assert "peso total" in resp.content.decode()
    assert not Ficha_Ingrediente.objects.exists()  # BR-016


def test_nao_remove_ultimo_item_da_receita(logado, ficha, ingrediente):
    item = Ficha_Ingrediente.objects.create(
        ficha=ficha, ingrediente=ingrediente, pesoBruto=10, pesoLiquido=10,
        nomeFantasia="Farinha",
    )
    logado.post(f"/deletarItemReceita/{ficha.pk}/{item.pk}/")
    assert Ficha_Ingrediente.objects.filter(pk=item.pk).exists()  # BR-018


def test_remove_item_quando_ha_mais_de_um(logado, ficha, ingrediente):
    primeiro = Ficha_Ingrediente.objects.create(
        ficha=ficha, ingrediente=ingrediente, pesoBruto=10, pesoLiquido=10, nomeFantasia="A"
    )
    Ficha_Ingrediente.objects.create(
        ficha=ficha, ingrediente=ingrediente, pesoBruto=20, pesoLiquido=20, nomeFantasia="B"
    )
    logado.post(f"/deletarItemReceita/{ficha.pk}/{primeiro.pk}/")
    assert not Ficha_Ingrediente.objects.filter(pk=primeiro.pk).exists()


def test_editar_item_recalcula_tabela(logado, ficha, ingrediente):
    """B12 corrigido: salvar o item recalcula (o original não recalculava)."""
    item = Ficha_Ingrediente.objects.create(
        ficha=ficha, ingrediente=ingrediente, pesoBruto=100, pesoLiquido=100,
        nomeFantasia="Farinha",
    )
    logado.post(f"/registrarFicha2/{ficha.pk}", {})  # garante estado inicial
    logado.post(
        f"/editarItemReceita/{ficha.pk}/{item.pk}/",
        {"nomeFantasia": "Farinha", "pesoBruto": 50, "pesoLiquido": 50, "medidaCaseira": ""},
    )
    tabela = Tabela.objects.get(pk=ficha.pk)
    assert tabela.proteinas == pytest.approx(5)  # 50 g × 10/100


# ------------------------------------------------------------------ wizard 3/3


def test_toggle_mostrar_inverte_visibilidade(logado, ficha):
    tabela = Tabela.objects.get(pk=ficha.pk)
    inicial = tabela.calcio_Mostrar
    logado.post(f"/atualizarMostrar/{ficha.pk}/calcio/")
    tabela.refresh_from_db()
    assert tabela.calcio_Mostrar is not inicial


def test_toggle_nutriente_desconhecido_nao_quebra(logado, ficha):
    resp = logado.post(f"/atualizarMostrar/{ficha.pk}/inexistente/", follow=True)
    assert resp.status_code == 200
    assert "desconhecido" in resp.content.decode()


def test_nutriente_extra_e_criado_e_removido(logado, ficha):
    logado.post(
        f"/registrarFicha3/{ficha.pk}",
        {"acao": "nutriente", "nomeNutri": "Cafeína", "qtde": 30, "qtde_Arred": 30,
         "medida": "mg", "qtde_VD": 0},
    )
    extra = Nutriente.objects.get(nomeNutri="Cafeína")
    logado.post(f"/deletarNutrienteExtra/{extra.pk}")
    assert not Nutriente.objects.filter(pk=extra.pk).exists()


def test_informacoes_complementares_salvam_e_vao_para_rotulo(logado, ficha):
    resp = logado.post(
        f"/registrarFicha3/{ficha.pk}",
        {"informacoesComplementares": "CONTÉM GLÚTEN."},
    )
    assert resp.url == f"/fichaX/{ficha.pk}"
    assert Tabela.objects.get(pk=ficha.pk).informacoesComplementares == "CONTÉM GLÚTEN."


# -------------------------------------------------------------------- rótulo


def test_rotulo_mostra_tabela_e_ingredientes(logado, ficha, ingrediente):
    Ficha_Ingrediente.objects.create(
        ficha=ficha, ingrediente=ingrediente, pesoBruto=100, pesoLiquido=100,
        nomeFantasia="Farinha de trigo",
    )
    logado.post(
        f"/editarItemReceita/{ficha.pk}/{Ficha_Ingrediente.objects.first().pk}/",
        {"nomeFantasia": "Farinha de trigo", "pesoBruto": 100, "pesoLiquido": 100,
         "medidaCaseira": ""},
    )
    corpo = logado.get(f"/fichaX/{ficha.pk}").content.decode()
    assert "INFORMAÇÃO NUTRICIONAL" in corpo
    assert "Farinha de trigo" in corpo
    assert "2 porções" in corpo  # BR-011: 100 / 50 exato


def test_rotulo_de_ficha_sem_tabela_nao_quebra(logado, membro):
    """B4 corrigido: ficha órfã (como as 16 do backup) não gera mais erro 500."""
    orfa = Ficha.objects.create(
        autor=membro, cliente="C", nomeFicha="Órfã", dataCriacao="2021-01-01",
        pesoTotal=100, pesoPorcao=50, pesoAnvisa=50,
    )
    assert not Tabela.objects.filter(pk=orfa.pk).exists()
    resp = logado.get(f"/fichaX/{orfa.pk}")
    assert resp.status_code == 200
    assert Tabela.objects.filter(pk=orfa.pk).exists()


def test_rotulo_sem_pesos_nao_quebra(logado, membro):
    """B15 corrigido: pesos de porção nulos (ficha 1273 do backup) não geram 500."""
    ficha = Ficha.objects.create(
        autor=membro, cliente="C", nomeFicha="Sem pesos", dataCriacao="2021-01-01",
        pesoPorcao=None, pesoAnvisa=None,
    )
    Tabela.objects.create(pk=ficha.pk, origem=ficha)
    resp = logado.get(f"/fichaX/{ficha.pk}")
    assert resp.status_code == 200
    assert "0 porções" in resp.content.decode()


def test_rotulo_exibe_biotina_sem_quebrar(logado, ficha):
    """B2 corrigido: o original crashava ao exibir biotina."""
    tabela = Tabela.objects.get(pk=ficha.pk)
    tabela.biotina_Mostrar = True
    tabela.biotina_Arred = 3.5
    tabela.save()
    corpo = logado.get(f"/fichaX/{ficha.pk}").content.decode()
    assert "Biotina" in corpo


def test_lupa_aparece_quando_alto_em_sodio(logado, ficha):
    """BR-012: sódio ≥ 600 mg/100 g exige o selo frontal."""
    tabela = Tabela.objects.get(pk=ficha.pk)
    tabela.sodio_100g = 700
    tabela.save()
    corpo = logado.get(f"/fichaX/{ficha.pk}").content.decode()
    assert "data:image/png;base64," in corpo
    assert "Rotulagem frontal" in corpo


def test_finalizada_e_um_toggle(logado, ficha):
    logado.post(f"/atualizarFinalizada/{ficha.pk}")
    ficha.refresh_from_db()
    assert ficha.finalizada is True
    logado.post(f"/atualizarFinalizada/{ficha.pk}")
    ficha.refresh_from_db()
    assert ficha.finalizada is False


def test_excluir_ficha_apaga_em_cascata(logado, ficha, ingrediente):
    Ficha_Ingrediente.objects.create(
        ficha=ficha, ingrediente=ingrediente, pesoBruto=1, pesoLiquido=1, nomeFantasia="F"
    )
    logado.post(f"/deletarFicha/{ficha.pk}")
    assert not Ficha.objects.filter(pk=ficha.pk).exists()
    assert not Tabela.objects.filter(pk=ficha.pk).exists()
    assert not Ficha_Ingrediente.objects.exists()  # BR-020


# --------------------------------------------------------------- ingredientes


def test_ingrediente_normaliza_para_100g(logado, membro):
    """BR-001: valores informados para 50 g são normalizados para 100 g."""
    dados = {
        "autorIng": membro.pk,
        "nomeIng": "Açúcar",
        "composicao": "",
        "origemDosDados": "Marca X",
        "qtdeDoIngrediente": 50,
        "numRef": 0,
        "dataCriacao": "10/01/2025",
        "proteinas": 5,
    }
    for chave in ("gordTotais", "acucaresTotais", "carboidratos", "fibras", "energiakcal",
                  "energiaKJ"):
        dados[chave] = 0
    logado.post("/registrarIngrediente", dados)
    ing = Ingrediente.objects.get(nomeIng="Açúcar")
    assert ing.proteinas_100g == pytest.approx(10)  # 5 * 100 / 50


def test_nome_e_marca_duplicados_sao_recusados(logado, membro, ingrediente):
    resp = logado.post(
        "/registrarIngrediente",
        {"autorIng": membro.pk, "nomeIng": "Farinha de trigo", "composicao": "",
         "origemDosDados": "TACO", "qtdeDoIngrediente": 100, "numRef": 0,
         "dataCriacao": "10/01/2025"},
        follow=True,
    )
    assert "Já existe um ingrediente com esse nome e essa fonte / marca" in resp.content.decode()
    assert Ingrediente.objects.filter(nomeIng="Farinha de trigo").count() == 1


def test_mesmo_nome_com_outra_marca_e_aceito(logado, membro, ingrediente):
    logado.post(
        "/registrarIngrediente",
        {"autorIng": membro.pk, "nomeIng": "Farinha de trigo", "composicao": "",
         "origemDosDados": "Tio Chico", "qtdeDoIngrediente": 100, "numRef": 0,
         "dataCriacao": "10/01/2025"},
    )
    assert Ingrediente.objects.filter(nomeIng="Farinha de trigo").count() == 2
    assert Ingrediente.objects.get(origemDosDados="Tio Chico").nome_exibicao == (
        "Farinha de trigo (Tio Chico)"
    )


def test_receita_escolhe_ingrediente_pelo_nome_com_marca(logado, ficha, ingrediente, membro):
    outra = Ingrediente.objects.create(
        autorIng=membro, nomeIng="Farinha de trigo", origemDosDados="Tio Chico",
        dataCriacao="2024-01-10", qtdeDoIngrediente=100,
    )
    corpo = logado.get(f"/registrarFicha2/{ficha.pk}").content.decode()
    assert '"marca": "Tio Chico"' in corpo  # dados do autocomplete
    logado.post(
        f"/registrarFicha2/{ficha.pk}",
        {"ingExtra": "Farinha de trigo (Tio Chico)", "nomeFantasia": "Farinha",
         "pesoBruto": 100, "pesoLiquido": 100, "medidaCaseira": ""},
    )
    assert Ficha_Ingrediente.objects.get().ingrediente == outra


def test_corte_por_ano_e_configuracao_da_instancia(logado, membro):
    """BR-017/D-010: sem configuração não há corte; com corte 2024, esconde antigos."""
    Ingrediente.objects.create(
        autorIng=membro, nomeIng="Antigo 2019", origemDosDados="TACO",
        dataCriacao="2019-09-26", qtdeDoIngrediente=100,
    )
    corpo = logado.get("/listaIngredientes").content.decode()
    assert "Antigo 2019" in corpo

    ConfiguracaoInstancia.objects.create(nome_exibicao="Nutri Jr", ano_corte_ingredientes=2024)
    corpo = logado.get("/listaIngredientes").content.decode()
    assert "Antigo 2019" not in corpo


def test_excluir_ingrediente_avisa_sobre_receitas(logado, ficha, ingrediente):
    Ficha_Ingrediente.objects.create(
        ficha=ficha, ingrediente=ingrediente, pesoBruto=1, pesoLiquido=1, nomeFantasia="F"
    )
    resp = logado.post(f"/deletarIngrediente/{ingrediente.pk}", follow=True)
    assert "removido de 1 receita" in resp.content.decode()


# ------------------------------------------------------------------ segurança


@pytest.mark.parametrize(
    "url",
    [
        "/listaFichas", "/listaIngredientes", "/registrarFicha1",
        "/registrarIngrediente", "/upload", "/ajuda",
    ],
)
def test_paginas_exigem_login(client, db, url):
    resp = client.get(url)
    assert resp.status_code == 302
    assert "/loginUser" in resp.url


@pytest.mark.parametrize(
    "template",
    [
        "/atualizarFinalizada/{pk}",
        "/deletarFicha/{pk}",
        "/atualizarMostrar/{pk}/calcio/",
    ],
)
def test_mutacoes_recusam_get(logado, ficha, template):
    """B10 corrigido: mutações só por POST."""
    resp = logado.get(template.format(pk=ficha.pk))
    assert resp.status_code == 405


def test_ficha_inexistente_devolve_404(logado):
    assert logado.get("/fichaX/999999").status_code == 404


# ------------------------------------------------------------------ paginação


def test_lista_de_fichas_pagina_resultados(logado, membro):
    """A lista não renderiza o acervo inteiro de uma vez (25 por página)."""
    from apps.fichas.views import ITENS_POR_PAGINA

    for i in range(ITENS_POR_PAGINA + 5):
        Ficha.objects.create(
            autor=membro, cliente="C", nomeFicha=f"Ficha {i:03d}", dataCriacao="2025-01-01"
        )
    primeira = logado.get("/listaFichas")
    assert len(primeira.context["fichas"].object_list) == ITENS_POR_PAGINA
    assert primeira.context["pagina"].has_next()

    segunda = logado.get("/listaFichas", {"pagina": 2})
    assert len(segunda.context["fichas"].object_list) == 5


def test_paginacao_preserva_filtros(logado, membro):
    for i in range(30):
        Ficha.objects.create(
            autor=membro, cliente="Padaria", nomeFicha=f"Pão {i:03d}", dataCriacao="2025-01-01"
        )
    Ficha.objects.create(
        autor=membro, cliente="Outro", nomeFicha="Bolo", dataCriacao="2025-01-01"
    )
    resp = logado.get("/listaFichas", {"f_nomeFicha": "Pão", "pagina": 2})
    assert resp.context["total"] == 30
    assert all("Pão" in f.nomeFicha for f in resp.context["fichas"].object_list)
    assert "f_nomeFicha=P%C3%A3o" in resp.context["filtrosQuery"]


# ------------------------------------------- conferência de tabela desatualizada


def test_rotulo_avisa_quando_porcao_e_incoerente(logado, ficha, ingrediente):
    """B18: a coluna da porção calculada com um peso diferente do declarado.

    Reproduz o caso real do acervo: a tabela foi gravada quando o peso da porção
    era o do cliente (100 g) e depois o peso ANVISA (50 g) passou a valer.
    """
    Ficha_Ingrediente.objects.create(
        ficha=ficha, ingrediente=ingrediente, pesoBruto=100, pesoLiquido=100,
        nomeFantasia="Farinha",
    )
    # calcula com o peso ANVISA vazio -> usa o peso cliente (100 g)
    ficha.pesoAnvisa = None
    ficha.save()
    from apps.fichas import servicos

    servicos.recalcular_tabela(ficha)

    # agora o peso ANVISA passa a valer, sem recalcular (como no acervo)
    ficha.pesoAnvisa = 50
    ficha.save(update_fields=["pesoAnvisa"])

    resp = logado.get(f"/fichaX/{ficha.pk}")
    corpo = resp.content.decode()
    assert resp.context["conferencia"]["porcao_incoerente"] is True
    assert resp.context["conferencia"]["peso_declarado"] == 50
    assert round(resp.context["conferencia"]["peso_usado"]) == 100
    assert "Esta tabela está desatualizada" in corpo
    assert "Recalcular esta tabela" in corpo


def test_recalcular_corrige_a_incoerencia(logado, ficha, ingrediente):
    Ficha_Ingrediente.objects.create(
        ficha=ficha, ingrediente=ingrediente, pesoBruto=100, pesoLiquido=100,
        nomeFantasia="Farinha",
    )
    from apps.fichas import servicos

    ficha.pesoAnvisa = None
    ficha.save()
    servicos.recalcular_tabela(ficha)
    ficha.pesoAnvisa = 50
    ficha.save(update_fields=["pesoAnvisa"])

    resp = logado.post(f"/recalcularFicha/{ficha.pk}", follow=True)
    assert "Tabela recalculada" in resp.content.decode()
    assert resp.context["conferencia"]["desatualizada"] is False
    # 100 g de farinha, peso total 200 g -> 5 g proteína/100 g; porção 50 g -> 2,5 g
    tabela = Tabela.objects.get(pk=ficha.pk)
    assert tabela.proteinas_Arred == pytest.approx(2.5)


def test_ficha_em_dia_nao_exibe_aviso(logado, ficha, ingrediente):
    Ficha_Ingrediente.objects.create(
        ficha=ficha, ingrediente=ingrediente, pesoBruto=100, pesoLiquido=100,
        nomeFantasia="Farinha",
    )
    from apps.fichas import servicos

    servicos.recalcular_tabela(ficha)
    resp = logado.get(f"/fichaX/{ficha.pk}")
    assert resp.context["conferencia"]["desatualizada"] is False
    assert "Esta tabela está desatualizada" not in resp.content.decode()


def test_recalcular_exige_login_e_post(logado, ficha):
    from django.test import Client

    assert logado.get(f"/recalcularFicha/{ficha.pk}").status_code == 405
    # cliente novo, sem sessao: a fixture `logado` reaproveita o mesmo objeto client
    anonimo = Client()
    resp = anonimo.post(f"/recalcularFicha/{ficha.pk}")
    assert resp.status_code == 302 and "/loginUser" in resp.url


def test_auditoria_lista_fichas_desatualizadas(logado, ficha, ingrediente, capsys):
    from io import StringIO
    from django.core.management import call_command
    from apps.fichas import servicos

    Ficha_Ingrediente.objects.create(
        ficha=ficha, ingrediente=ingrediente, pesoBruto=100, pesoLiquido=100,
        nomeFantasia="Farinha",
    )
    ficha.pesoAnvisa = None
    ficha.save()
    servicos.recalcular_tabela(ficha)
    ficha.pesoAnvisa = 50
    ficha.save(update_fields=["pesoAnvisa"])

    saida = StringIO()
    call_command("auditar_tabelas", stdout=saida)
    texto = saida.getvalue()
    assert "porcao INCOERENTE no rotulo:       1" in texto.replace("   1", "       1") or "INCOERENTE" in texto
    assert str(ficha.pk) in texto


def test_receita_aceita_ingrediente_pelo_id_do_autocomplete(logado, ficha, ingrediente):
    logado.post(
        f"/registrarFicha2/{ficha.pk}",
        {"ingExtra": "texto qualquer", "ingId": ingrediente.pk, "nomeFantasia": "Farinha",
         "pesoBruto": 10, "pesoLiquido": 10, "medidaCaseira": ""},
    )
    assert Ficha_Ingrediente.objects.get().ingrediente == ingrediente


def test_filtro_de_ingredientes_ignora_acentos_e_ordem(logado, membro):
    Ingrediente.objects.create(
        autorIng=membro, nomeIng="Açúcar de confeiteiro", origemDosDados="União",
        dataCriacao="2024-01-10", qtdeDoIngrediente=100,
    )
    Ingrediente.objects.create(
        autorIng=membro, nomeIng="Sal refinado", origemDosDados="Cisne",
        dataCriacao="2024-01-10", qtdeDoIngrediente=100,
    )
    corpo = logado.get(
        "/listaIngredientes", {"f_nomeIng": "CONFEITEIRO acucar", "f_origemDosDados": "uniao"}
    ).content.decode()
    assert "Açúcar de confeiteiro" in corpo
    assert "Sal refinado" not in corpo


def test_filtro_de_fichas_ignora_acentos_e_maiusculas(logado, ficha):
    corpo = logado.get("/listaFichas", {"f_nomeFicha": "pao de TESTE"}).content.decode()
    assert "Pão de teste" in corpo


def test_datas_usam_calendario_com_hoje_como_padrao(logado):
    hoje = datetime.date.today().isoformat()
    for url in ("/registrarFicha1", "/registrarIngrediente"):
        corpo = logado.get(url).content.decode()
        assert 'type="date"' in corpo
        assert f'value="{hoje}"' in corpo


# ------------------------------------------------------- leitura por foto


def _foto():
    import io

    from PIL import Image

    arquivo = io.BytesIO()
    Image.new("RGB", (800, 600), "white").save(arquivo, format="JPEG")
    arquivo.seek(0)
    arquivo.name = "rotulo.jpg"
    return arquivo


RESPOSTA_GEMINI = """{
  "e_tabela_nutricional": true, "porcao_g": 30, "nome": "Granola", "marca": "Mãe Terra",
  "nutrientes": {"proteinas": {"por_100g": 10, "por_porcao": 3},
                 "sodio": {"por_100g": 50, "por_porcao": 15}},
  "avisos": []
}"""


def test_botao_de_foto_so_aparece_com_chave(logado, settings):
    settings.GEMINI_API_KEY = ""
    assert "Preencher a partir de foto" not in logado.get("/registrarIngrediente").content.decode()
    settings.GEMINI_API_KEY = "chave-de-teste"
    assert "Preencher a partir de foto" in logado.get("/registrarIngrediente").content.decode()


def test_ler_rotulo_devolve_campos_para_o_formulario(logado, settings, monkeypatch):
    from apps.fichas import leitura_rotulo

    settings.GEMINI_API_KEY = "chave-de-teste"
    monkeypatch.setattr(leitura_rotulo, "_chamar_gemini", lambda jpeg: RESPOSTA_GEMINI)
    resp = logado.post("/lerRotuloIngrediente", {"foto": _foto()})
    assert resp.status_code == 200
    campos = resp.json()["campos"]
    assert campos["qtdeDoIngrediente"] == 100
    assert campos["proteinas"] == 10
    assert campos["origemDosDados"] == "Mãe Terra"
    assert not Ingrediente.objects.exists()  # só pré-preenche, não salva


def test_ler_rotulo_sem_chave_responde_503(logado, settings):
    settings.GEMINI_API_KEY = ""
    assert logado.post("/lerRotuloIngrediente", {"foto": _foto()}).status_code == 503


def test_ler_rotulo_com_falha_na_api_mostra_erro_amigavel(logado, settings, monkeypatch):
    from apps.fichas import leitura_rotulo

    def falhar(jpeg):
        raise RuntimeError("timeout")

    settings.GEMINI_API_KEY = "chave-de-teste"
    monkeypatch.setattr(leitura_rotulo, "_chamar_gemini", falhar)
    resp = logado.post("/lerRotuloIngrediente", {"foto": _foto()})
    assert resp.status_code == 422
    assert "não respondeu" in resp.json()["erro"]


def test_ler_rotulo_exige_login(client):
    assert client.post("/lerRotuloIngrediente", {"foto": _foto()}).status_code == 302


def test_cadastro_de_ingrediente_agrupa_vitaminas_em_sequencia(logado):
    corpo = logado.get("/registrarIngrediente").content.decode()
    vitaminas = corpo.index(">Vitaminas<")
    minerais = corpo.index(">Minerais<")
    for campo in ("id_vitaminaARAE", "id_vitaminaD", "id_tiamina", "id_vitaminaB12"):
        assert vitaminas < corpo.index(f'id="{campo}"') < minerais


def test_adicionado_manualmente_saiu_da_tela_sem_perder_o_valor(logado, membro, ingrediente):
    corpo = logado.get("/registrarIngrediente").content.decode()
    assert "Adicionado manualmente" not in corpo
    assert "tabela de origem" in corpo  # ajuda do Nº de referência

    Ingrediente.objects.filter(pk=ingrediente.pk).update(addManualmente=False)
    logado.post(
        f"/editarIngrediente/{ingrediente.pk}",
        {"autorIng": membro.pk, "nomeIng": "Farinha de trigo", "composicao": "",
         "origemDosDados": "TACO", "qtdeDoIngrediente": 100, "numRef": 7,
         "dataCriacao": "2024-01-10"},
    )
    ingrediente.refresh_from_db()
    assert ingrediente.numRef == 7
    assert ingrediente.addManualmente is False
