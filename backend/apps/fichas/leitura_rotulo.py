"""Leitura da tabela nutricional a partir de uma foto (pré-preenche o cadastro de
ingrediente). Usa o Gemini; nada é salvo aqui — a pessoa revisa e salva o formulário.

Fluxo: foto → `preparar_imagem` (gira pelo EXIF, reduz, JPEG) → Gemini devolve JSON
no esquema `LeituraRotulo` → `montar_resultado` escolhe a coluna (100 g ou porção),
confere uma contra a outra e devolve os campos para o formulário.
"""
import base64
import io
import logging

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field, ValidationError, create_model

from apps.fichas.dominio.nutrientes import NUTRIENTES, unidade_armazenada

logger = logging.getLogger(__name__)

LADO_MAXIMO_PX = 2048
# Diferença tolerada entre a coluna de 100 g e a de porção convertida: os rótulos
# arredondam, então só marcamos para conferência o que diverge além disso.
TOLERANCIA_RELATIVA = 0.15
TOLERANCIA_ABSOLUTA = 1.0


class LeituraIndisponivel(Exception):
    """Sem chave configurada."""


class FalhaNaLeitura(Exception):
    """Foto ilegível, resposta inválida ou erro na API. A mensagem vai para o usuário."""


class Valor(BaseModel):
    por_100g: float | None = Field(
        default=None, description="Valor na coluna '100 g' (ou 100 ml). null se não houver."
    )
    por_porcao: float | None = Field(
        default=None, description="Valor na coluna da porção. null se não houver."
    )


def _rotulo(n):
    return n.rotulo or "Valor energético (kJ)"


Nutrientes = create_model(
    "Nutrientes",
    **{
        n.chave: (
            Valor | None,
            Field(default=None, description=f"{_rotulo(n)}, em {unidade_armazenada(n)}"),
        )
        for n in NUTRIENTES
    },
)


class LeituraRotulo(BaseModel):
    e_tabela_nutricional: bool = Field(
        description="false se a imagem não mostra uma tabela nutricional legível."
    )
    porcao_g: float | None = Field(
        default=None, description="Tamanho da porção em gramas (ou ml), se informado."
    )
    nome: str | None = Field(default=None, description="Nome do produto, se aparecer.")
    marca: str | None = Field(default=None, description="Marca do produto, se aparecer.")
    composicao: str | None = Field(
        default=None, description="Lista de ingredientes do produto, se aparecer."
    )
    nutrientes: Nutrientes
    avisos: list[str] = Field(
        default_factory=list,
        description="Problemas de leitura em português: trechos ilegíveis, cortados etc.",
    )


INSTRUCOES = """\
Você lê tabelas de informação nutricional de rótulos brasileiros (ANVISA) em fotos.

- Transcreva os números exatamente como estão no rótulo. Vírgula é separador decimal.
- Preencha por_100g com a coluna de 100 g (ou 100 ml) e por_porcao com a coluna da
  porção, quando existirem. Ignore a coluna de %VD.
- Converta para a unidade pedida em cada campo quando o rótulo usar outra
  (ex.: μg → mg divide por 1000) e registre a conversão em avisos.
- Vitamina A vai em UM só campo, sem converter nem copiar para os outros:
  "RAE" ou "EAR" → vitaminaARAE; "RE" ou "ER" → RE; "retinol" → retinol.
  Se o rótulo não especificar: com coluna de 100 g (rótulo novo) → vitaminaARAE;
  só com a porção (rótulo antigo) → RE. Diga em avisos qual campo usou e por quê,
  chamando-o de "Vitamina A — RAE", "Vitamina A — RE" ou "Vitamina A — retinol".
- Nos avisos, use os nomes dos nutrientes em português, nunca os nomes dos campos.
- "Zero", "0", "não contém quantidade significativa" e asteriscos que indiquem isso
  viram 0. Nutriente que não aparece no rótulo fica null — não invente valores.
- Se algum número estiver ilegível, deixe null e explique em avisos.
"""


def leitura_habilitada() -> bool:
    return bool(settings.GEMINI_API_KEY)


def preparar_imagem(conteudo: bytes) -> bytes:
    """Corrige a rotação da câmera, limita o tamanho e converte para JPEG."""
    try:
        imagem = Image.open(io.BytesIO(conteudo))
        imagem = ImageOps.exif_transpose(imagem).convert("RGB")
    except (UnidentifiedImageError, OSError) as erro:
        raise FalhaNaLeitura("Não foi possível abrir a imagem. Envie uma foto JPG ou PNG.") from erro
    imagem.thumbnail((LADO_MAXIMO_PX, LADO_MAXIMO_PX))
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=85)
    return saida.getvalue()


def _chamar_gemini(jpeg: bytes) -> str:
    """Única função que fala com a API (os testes substituem esta)."""
    from google import genai  # import tardio: só carrega o SDK quando usado

    cliente = genai.Client(api_key=settings.GEMINI_API_KEY)
    resposta = cliente.interactions.create(
        model=settings.GEMINI_MODELO,
        input=[
            {"type": "text", "text": INSTRUCOES},
            {
                "type": "image",
                "data": base64.b64encode(jpeg).decode("ascii"),
                "mime_type": "image/jpeg",
            },
        ],
        generation_config={"thinking_level": settings.GEMINI_RACIOCINIO},
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": LeituraRotulo.model_json_schema(),
        },
        timeout=settings.GEMINI_TIMEOUT,
    )
    return resposta.output_text


def _diverge(por_100g: float, convertido: float) -> bool:
    diferenca = abs(por_100g - convertido)
    return diferenca > max(TOLERANCIA_ABSOLUTA, TOLERANCIA_RELATIVA * max(por_100g, convertido))


def montar_resultado(leitura: LeituraRotulo) -> dict:
    """Converte a leitura nos campos do IngredienteForm.

    Prefere a coluna de 100 g (qtdeDoIngrediente = 100). Sem ela, usa a da porção
    com qtdeDoIngrediente = tamanho da porção — o normalizar_100g faz o resto (BR-001).
    """
    if not leitura.e_tabela_nutricional:
        raise FalhaNaLeitura(
            "Não encontrei uma tabela nutricional legível na foto. "
            "Tente de novo com a tabela inteira, reta e sem reflexo."
        )

    valores = {n.chave: getattr(leitura.nutrientes, n.chave) for n in NUTRIENTES}
    tem_100g = any(v and v.por_100g is not None for v in valores.values())
    tem_porcao = bool(leitura.porcao_g) and any(
        v and v.por_porcao is not None for v in valores.values()
    )
    if not tem_100g and not tem_porcao:
        raise FalhaNaLeitura("Não consegui ler os valores da tabela. Tente outra foto.")

    campos: dict = {"qtdeDoIngrediente": 100 if tem_100g else leitura.porcao_g}
    conferir: list[str] = []
    for chave, valor in valores.items():
        if valor is None:
            continue
        escolhido = valor.por_100g if tem_100g else valor.por_porcao
        if escolhido is None:
            continue
        campos[chave] = escolhido
        if tem_100g and valor.por_porcao is not None and leitura.porcao_g:
            convertido = valor.por_porcao * 100 / leitura.porcao_g
            if _diverge(valor.por_100g, convertido):
                conferir.append(chave)

    for campo, origem in (("nomeIng", leitura.nome), ("origemDosDados", leitura.marca),
                          ("composicao", leitura.composicao)):
        if origem:
            campos[campo] = origem.strip()

    avisos = list(leitura.avisos)
    if conferir:
        avisos.insert(0, "As colunas de 100 g e da porção não batem nos campos em vermelho: confira.")
    return {"campos": campos, "conferir": conferir, "avisos": avisos}


def ler_rotulo(conteudo: bytes) -> dict:
    if not leitura_habilitada():
        raise LeituraIndisponivel
    jpeg = preparar_imagem(conteudo)
    try:
        bruto = _chamar_gemini(jpeg)
    except Exception as erro:  # o SDK tem várias hierarquias de erro; todas viram falha
        logger.exception("Falha ao chamar o Gemini")
        raise FalhaNaLeitura(
            "O serviço de leitura não respondeu. Tente de novo em instantes."
        ) from erro
    try:
        leitura = LeituraRotulo.model_validate_json(bruto)
    except ValidationError as erro:
        logger.warning("Resposta do Gemini fora do esquema: %s", erro)
        raise FalhaNaLeitura("Não consegui interpretar a leitura da foto. Tente outra foto.") from erro
    return montar_resultado(leitura)
