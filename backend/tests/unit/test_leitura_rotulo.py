"""Leitura da tabela nutricional por foto: escolha de coluna, conferência e imagem.
A API do Gemini nunca é chamada aqui."""
import io

import pytest
from PIL import Image

from apps.fichas import leitura_rotulo as lr


def _leitura(porcao_g=None, **nutrientes):
    return lr.LeituraRotulo(
        e_tabela_nutricional=True,
        porcao_g=porcao_g,
        nutrientes={chave: valor for chave, valor in nutrientes.items()},
    )


def test_prefere_coluna_de_100g():
    resultado = lr.montar_resultado(
        _leitura(porcao_g=30, proteinas={"por_100g": 10, "por_porcao": 3},
                 sodio={"por_100g": 400, "por_porcao": 120})
    )
    assert resultado["campos"]["qtdeDoIngrediente"] == 100
    assert resultado["campos"]["proteinas"] == 10
    assert resultado["campos"]["sodio"] == 400
    assert resultado["conferir"] == []


def test_rotulo_antigo_so_com_porcao_usa_tamanho_da_porcao():
    """Sem coluna de 100 g, o normalizar_100g converte a partir da porção (BR-001)."""
    resultado = lr.montar_resultado(_leitura(porcao_g=25, proteinas={"por_porcao": 2.5}))
    assert resultado["campos"]["qtdeDoIngrediente"] == 25
    assert resultado["campos"]["proteinas"] == 2.5


def test_colunas_que_nao_batem_vao_para_conferencia():
    # porção 50 g com 20 g de carboidrato = 40 g/100 g, mas a coluna diz 4
    resultado = lr.montar_resultado(
        _leitura(porcao_g=50, carboidratos={"por_100g": 4, "por_porcao": 20},
                 proteinas={"por_100g": 6, "por_porcao": 3})
    )
    assert resultado["conferir"] == ["carboidratos"]
    assert "não batem" in resultado["avisos"][0]


def test_arredondamento_do_rotulo_nao_gera_alarme_falso():
    # 0,4 g na porção de 30 g → 1,33 g/100 g; rótulo diz 1,3
    resultado = lr.montar_resultado(
        _leitura(porcao_g=30, gordSat={"por_100g": 1.3, "por_porcao": 0.4})
    )
    assert resultado["conferir"] == []


def test_imagem_sem_tabela_e_recusada():
    with pytest.raises(lr.FalhaNaLeitura, match="tabela nutricional"):
        lr.montar_resultado(lr.LeituraRotulo(e_tabela_nutricional=False, nutrientes={}))


def test_tabela_sem_valores_e_recusada():
    with pytest.raises(lr.FalhaNaLeitura):
        lr.montar_resultado(_leitura(porcao_g=None, proteinas={"por_porcao": 3}))


def test_nome_marca_e_composicao_vao_para_os_campos():
    leitura = _leitura(proteinas={"por_100g": 1})
    leitura.nome, leitura.marca, leitura.composicao = " Açúcar ", "União", "açúcar"
    campos = lr.montar_resultado(leitura)["campos"]
    assert (campos["nomeIng"], campos["origemDosDados"], campos["composicao"]) == (
        "Açúcar", "União", "açúcar"
    )


def test_esquema_cobre_todos_os_nutrientes_do_sistema():
    from apps.fichas.dominio.nutrientes import NUTRIENTES

    propriedades = lr.LeituraRotulo.model_json_schema()["$defs"]["Nutrientes"]["properties"]
    assert set(propriedades) == {n.chave for n in NUTRIENTES}


def test_preparar_imagem_reduz_e_converte_para_jpeg():
    original = io.BytesIO()
    Image.new("RGBA", (4000, 3000), "white").save(original, format="PNG")
    jpeg = lr.preparar_imagem(original.getvalue())
    imagem = Image.open(io.BytesIO(jpeg))
    assert imagem.format == "JPEG"
    assert max(imagem.size) == lr.LADO_MAXIMO_PX


def test_arquivo_que_nao_e_imagem_e_recusado():
    with pytest.raises(lr.FalhaNaLeitura, match="abrir a imagem"):
        lr.preparar_imagem(b"isto nao e uma imagem")


def test_vitamina_a_e_pedida_em_microgramas_como_na_taco():
    """Os dados da TACO guardam retinol/RE/RAE em μg; pedir mg dividiria por 1000."""
    propriedades = lr.LeituraRotulo.model_json_schema()["$defs"]["Nutrientes"]["properties"]
    for chave in ("retinol", "RE", "vitaminaARAE"):
        assert propriedades[chave]["description"].endswith("em μg")
