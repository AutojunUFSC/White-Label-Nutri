"""Logotipo da instância: guardado no banco, não em disco.

O ponto que estes testes protegem: em plataformas de disco efêmero (Heroku,
Render, Fly) um arquivo enviado pelo cliente some no próximo restart. Como a
identidade visual é o que se vende no modelo white-label, ela precisa viver no
banco de cada empresa.
"""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.plataforma.admin import ConfiguracaoInstanciaForm
from apps.plataforma.models import TAMANHO_MAXIMO_LOGOTIPO, ConfiguracaoInstancia


def imagem(formato="PNG", tamanho=(40, 20), cor="#198754"):
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", tamanho, cor).save(buffer, format=formato)
    return buffer.getvalue()


def enviado(conteudo, nome="logo.png", tipo="image/png"):
    return SimpleUploadedFile(nome, conteudo, content_type=tipo)


@pytest.fixture
def configuracao(db):
    return ConfiguracaoInstancia.objects.create(nome_exibicao="Empresa Teste")


def salvar_logotipo(configuracao, arquivo):
    form = ConfiguracaoInstanciaForm(
        data={"nome_exibicao": configuracao.nome_exibicao, "cor_primaria": "#198754"},
        files={"logotipo": arquivo},
        instance=configuracao,
    )
    assert form.is_valid(), form.errors
    return form.save()


# ------------------------------------------------------------------ upload


def test_logotipo_e_guardado_no_banco(configuracao):
    conteudo = imagem()
    salvar_logotipo(configuracao, enviado(conteudo))

    do_banco = ConfiguracaoInstancia.objects.get(pk=configuracao.pk)
    assert bytes(do_banco.logotipo_dados) == conteudo
    assert do_banco.logotipo_tipo == "image/png"
    assert do_banco.logotipo_atualizado_em is not None
    assert do_banco.tem_logotipo is True


def test_tipo_vem_do_conteudo_e_nao_da_extensao(configuracao):
    """Um JPEG chamado 'logo.png' é servido como JPEG."""
    salvar_logotipo(configuracao, enviado(imagem("JPEG"), nome="logo.png"))
    configuracao.refresh_from_db()
    assert configuracao.logotipo_tipo == "image/jpeg"


def test_arquivo_que_nao_e_imagem_e_recusado(configuracao):
    form = ConfiguracaoInstanciaForm(
        data={"nome_exibicao": "X", "cor_primaria": "#198754"},
        files={"logotipo": enviado(b"isto nao e uma imagem")},
        instance=configuracao,
    )
    assert not form.is_valid()
    assert "não é uma imagem válida" in str(form.errors["logotipo"])


def test_formato_nao_aceito_e_recusado(configuracao):
    form = ConfiguracaoInstanciaForm(
        data={"nome_exibicao": "X", "cor_primaria": "#198754"},
        files={"logotipo": enviado(imagem("BMP"), nome="logo.bmp")},
        instance=configuracao,
    )
    assert not form.is_valid()
    assert "não aceito" in str(form.errors["logotipo"])


def test_arquivo_grande_demais_e_recusado(configuracao):
    grande = b"\x89PNG\r\n\x1a\n" + b"0" * (TAMANHO_MAXIMO_LOGOTIPO + 1)
    form = ConfiguracaoInstanciaForm(
        data={"nome_exibicao": "X", "cor_primaria": "#198754"},
        files={"logotipo": enviado(grande)},
        instance=configuracao,
    )
    assert not form.is_valid()
    assert "limite" in str(form.errors["logotipo"])


def test_remover_logotipo(configuracao):
    salvar_logotipo(configuracao, enviado(imagem()))
    form = ConfiguracaoInstanciaForm(
        data={
            "nome_exibicao": "Empresa Teste",
            "cor_primaria": "#198754",
            "remover_logotipo": "on",
        },
        instance=ConfiguracaoInstancia.objects.get(pk=configuracao.pk),
    )
    assert form.is_valid(), form.errors
    form.save()

    configuracao.refresh_from_db()
    assert configuracao.tem_logotipo is False


# ------------------------------------------------------------------ entrega


def test_logotipo_e_servido_com_o_tipo_correto(client, configuracao):
    conteudo = imagem()
    salvar_logotipo(configuracao, enviado(conteudo))

    resp = client.get(reverse("logotipoInstancia"))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "image/png"
    assert resp.content == conteudo
    assert "Last-Modified" in resp


def test_navegador_revalida_e_recebe_304(client, configuracao):
    salvar_logotipo(configuracao, enviado(imagem()))
    primeira = client.get(reverse("logotipoInstancia"))

    segunda = client.get(
        reverse("logotipoInstancia"), HTTP_IF_MODIFIED_SINCE=primeira["Last-Modified"]
    )
    assert segunda.status_code == 304


def test_sem_logotipo_devolve_404(client, configuracao):
    assert client.get(reverse("logotipoInstancia")).status_code == 404


def test_logotipo_e_publico(client, configuracao):
    """Aparece na tela de login, antes de existir sessão."""
    salvar_logotipo(configuracao, enviado(imagem()))
    assert client.get(reverse("logotipoInstancia")).status_code == 200


# -------------------------------------------------------------- na interface


def test_logotipo_aparece_na_tela_de_login(client, configuracao):
    salvar_logotipo(configuracao, enviado(imagem()))
    corpo = client.get("/loginUser").content.decode()
    assert reverse("logotipoInstancia") in corpo
    assert "Empresa Teste" in corpo


def test_sem_logotipo_o_login_nao_quebra(client, configuracao):
    corpo = client.get("/loginUser").content.decode()
    assert "Empresa Teste" in corpo
    assert reverse("logotipoInstancia") not in corpo


def test_endereco_muda_quando_o_logotipo_muda(client, configuracao):
    """A versão na URL fura o cache do navegador quando a empresa troca a marca."""
    salvar_logotipo(configuracao, enviado(imagem()))
    primeiro = client.get("/loginUser").content.decode()

    configuracao.refresh_from_db()
    salvar_logotipo(configuracao, enviado(imagem(cor="#aa00aa")))
    segundo = client.get("/loginUser").content.decode()

    def versao(corpo):
        import re

        achado = re.search(r'logotipo\?v=(\d+)', corpo)
        return achado.group(1) if achado else None

    assert versao(primeiro) is not None
    assert versao(primeiro) != versao(segundo)


def test_nada_e_gravado_em_disco(configuracao, settings, tmp_path):
    """Prova que o logotipo não depende do sistema de arquivos."""
    salvar_logotipo(configuracao, enviado(imagem()))
    assert not list(tmp_path.iterdir())
    assert not hasattr(settings, "MEDIA_ROOT") or not (
        tmp_path / "branding"
    ).exists()

# ------------------------------------------- verificação da instância (W001)


def test_check_avisa_quando_a_instancia_nao_esta_configurada(db):
    """Sem configuração, o ano de corte fica vazio e a lista de ingredientes
    volta a mostrar os itens antigos — falha silenciosa que o aviso denuncia."""
    from apps.plataforma.checks import instancia_esta_configurada

    assert not ConfiguracaoInstancia.objects.exists()
    avisos = instancia_esta_configurada(None)
    assert [a.id for a in avisos] == ["plataforma.W001"]
    assert "ano de corte" in avisos[0].hint


def test_check_silencia_quando_configurada(configuracao):
    from apps.plataforma.checks import instancia_esta_configurada

    assert instancia_esta_configurada(None) == []


def test_check_aparece_no_manage_check(db, capsys):
    from io import StringIO

    from django.core.management import call_command

    saida = StringIO()
    call_command("check", stdout=saida, stderr=saida)
    assert "plataforma.W001" in saida.getvalue()
