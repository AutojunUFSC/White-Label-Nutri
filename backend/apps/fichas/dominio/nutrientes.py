"""Registro único dos 46 nutrientes do sistema.

Única fonte de verdade para: unidade padrão, referência de %VD (BR-008), limites
de "declarável como zero" (BR-007), visibilidade padrão na tabela final, rótulo e
ordem/indentação no rótulo ANVISA (BR-030).

NÃO alterar sem registrar a decisão em docs/ARQUITETURA.md: qualquer mudança
aqui muda rótulos já emitidos aos clientes.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class NutrienteDef:
    chave: str                 # prefixo das colunas no banco (ex.: "proteinas")
    unidade: str               # unidade exibida (default de X_unidadeMd)
    vd_referencia: float | None  # None → %VD forçado a 0 (nunca exibido com valor)
    mostrar_padrao: bool       # default de X_Mostrar
    rotulo: str | None         # texto no rótulo final; None = kcal/kJ (linha conjunta)
    ordem_rotulo: int | None   # posição em montarTabelaFinal; None = não tem linha própria
    indentado: bool = False    # BR-030: linha exibida com recuo no rótulo
    limite_zero: float | None = None  # BR-007: valor ≤ limite → declarado 0
    vd_em_branco: bool = False  # BR-009: %VD exibido como "" (açúcares totais)


# Ordem desta tupla = ordem de declaração no model Tabela (colunas do banco).
# ordem_rotulo = ordem das linhas em montarTabelaFinal (rótulo ANVISA).
NUTRIENTES: tuple[NutrienteDef, ...] = (
    NutrienteDef("proteinas", "g", 50, True, "Proteínas", 5, limite_zero=0.5),
    NutrienteDef("gordTotais", "g", 65, True, "Gorduras Totais", 6, limite_zero=0.5),
    NutrienteDef("carboidratos", "g", 300, True, "Carboidratos totais", 2, limite_zero=0.5),
    NutrienteDef("fibras", "g", 25, True, "Fibra Alimentar", 12, limite_zero=0.5),
    NutrienteDef("energiakcal", "kcal", 2000, True, "Valor energético", 1, limite_zero=4),
    NutrienteDef("energiaKJ", "kJ", 8400, True, None, None, limite_zero=17),
    NutrienteDef("calcio", "mg", 1000, False, "Cálcio", 14),
    NutrienteDef("ferro", "mg", 14, False, "Ferro", 16),
    NutrienteDef("magnesio", "mg", 420, False, "Magnésio", 18),
    NutrienteDef("fosforo", "mg", 700, False, "Fósforo", 17),
    NutrienteDef("potassio", "mg", None, False, "Potássio", 20),
    NutrienteDef("sodio", "mg", 2000, True, "Sódio", 13, limite_zero=5),
    NutrienteDef("zinco", "mg", 11, False, "Zinco", 21),
    NutrienteDef("cobre", "mg", 0.9, False, "Cobre", 15),
    NutrienteDef("manganes", "mg", 3, False, "Manganês", 19),
    NutrienteDef("retinol", "mg", None, False, "Retinol", 22),
    NutrienteDef("RE", "mg", None, False, "RE", 23),
    NutrienteDef("vitaminaARAE", "mg", None, False, "RAE", 24),
    NutrienteDef("vitaminaC", "mg", 100, False, "Vitamina C", 29),
    NutrienteDef("tiamina", "mg", 1.2, False, "Tiamina", 25),
    NutrienteDef("riboflavina", "mg", 1.2, False, "Riboflavina", 26),
    NutrienteDef("niancina", "mg", 15, False, "Niancina", 27),
    NutrienteDef("piridoxina", "mg", None, False, "Piridoxina", 28),
    NutrienteDef("gordSat", "g", 20, True, "Gorduras Saturadas", 7, indentado=True, limite_zero=0.2),
    NutrienteDef("gordTrans", "g", None, True, "Gorduras Trans", 8, indentado=True, limite_zero=0.2),
    NutrienteDef("gordPoli", "g", None, False, "Gorduras polissaturadas", 10, indentado=True),
    NutrienteDef("gordMono", "g", None, False, "Gorduras monosaturadas", 9, indentado=True),
    NutrienteDef("colesterol", "mg", 300, False, "Colesterol", 11, indentado=True),
    NutrienteDef("acucaresadd", "g", 50, True, "Açúcares adicionados", 4, indentado=True),
    NutrienteDef("omega6", "g", 18, False, "Omega 6", 30),
    NutrienteDef("omega3", "mg", 4000, False, "Omega 3", 31),
    NutrienteDef("vitaminaD", "μg", 15, False, "Vitamina D", 32),
    NutrienteDef("vitaminaE", "mg", 15, False, "Vitamina E", 33),
    NutrienteDef("vitaminaK", "μg", 120, False, "Vitamina K", 34),
    NutrienteDef("biotina", "μg", 30, False, "Biotina", 35),
    NutrienteDef("acidoFolico", "μg", 400, False, "Ácido fólico", 36),
    NutrienteDef("acidoPantotenico", "mg", 5, False, "Ácido pantotênico", 37),
    NutrienteDef("vitaminaB12", "μg", 2.4, False, "Vitamina B12", 38),
    NutrienteDef("cloreto", "mg", 2300, False, "Cloreto", 39),
    NutrienteDef("cromo", "μg", 35, False, "Cromo", 40),
    NutrienteDef("fluor", "mg", 4, False, "Flúor", 41),
    NutrienteDef("iodo", "μg", 150, False, "Iodo", 42),
    NutrienteDef("molibdenio", "μg", 45, False, "Molibdênio", 43),
    # A referência de %VD do selênio (11) diverge da IN 75/2020 (34 μg); mantida
    # deliberadamente para não alterar rótulos já emitidos — ver BR-008.
    NutrienteDef("selenio", "μg", 11, False, "Selenio", 44),
    NutrienteDef("colina", "mg", 550, False, "Colina", 45),
    NutrienteDef("acucaresTotais", "g", None, True, "Açúcares totais", 3,
                 indentado=True, vd_em_branco=True),
)

POR_CHAVE: dict[str, NutrienteDef] = {n.chave: n for n in NUTRIENTES}

# Linhas do rótulo em ordem de exibição (BR-030). "Valor energético" só existe
# se kcal E kJ estiverem marcados como mostrar.
ORDEM_ROTULO: tuple[NutrienteDef, ...] = tuple(
    sorted((n for n in NUTRIENTES if n.ordem_rotulo is not None),
           key=lambda n: n.ordem_rotulo)
)

# Unidade em que o valor está GUARDADO no ingrediente, quando difere de `unidade`.
# Os dados da TACO trazem retinol, RE e RAE em μg (fígado bovino: 14.574 μg/100 g),
# mas o registro acima exibe "mg". Usado no cadastro de ingrediente e na leitura
# por foto; o rótulo final continua usando `unidade` (não alterado aqui).
UNIDADE_ARMAZENADA: dict[str, str] = {"retinol": "μg", "RE": "μg", "vitaminaARAE": "μg"}


def unidade_armazenada(n: NutrienteDef) -> str:
    return UNIDADE_ARMAZENADA.get(n.chave, n.unidade)


# Agrupamento e ordem dos campos no cadastro de ingrediente, como numa tabela
# nutricional real. Só afeta a tela de cadastro, não o rótulo.
GRUPOS_CADASTRO: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Tabela principal", (
        "energiakcal", "energiaKJ", "carboidratos", "acucaresTotais", "acucaresadd",
        "proteinas", "gordTotais", "gordSat", "gordTrans", "fibras", "sodio",
    )),
    ("Outras gorduras", ("gordMono", "gordPoli", "colesterol", "omega3", "omega6")),
    ("Vitaminas", (
        "retinol", "RE", "vitaminaARAE", "vitaminaD", "vitaminaE", "vitaminaK",
        "vitaminaC", "tiamina", "riboflavina", "niancina", "acidoPantotenico",
        "piridoxina", "biotina", "acidoFolico", "vitaminaB12", "colina",
    )),
    ("Minerais", (
        "calcio", "ferro", "magnesio", "fosforo", "potassio", "zinco", "cobre",
        "manganes", "selenio", "iodo", "cromo", "fluor", "molibdenio", "cloreto",
    )),
)

# Nomes mais claros que o rótulo do registro, só para o cadastro.
ROTULO_CADASTRO: dict[str, str] = {
    "energiakcal": "Valor energético",
    "energiaKJ": "Valor energético",
    "retinol": "Vitamina A — retinol",
    "RE": "Vitamina A — RE",
    "vitaminaARAE": "Vitamina A — RAE",
    "tiamina": "Tiamina (B1)",
    "riboflavina": "Riboflavina (B2)",
    "niancina": "Niacina (B3)",
    "acidoPantotenico": "Ácido pantotênico (B5)",
    "piridoxina": "Piridoxina (B6)",
    "biotina": "Biotina (B7)",
    "acidoFolico": "Ácido fólico (B9)",
    "gordPoli": "Gorduras poli-insaturadas",
    "gordMono": "Gorduras monoinsaturadas",
    "selenio": "Selênio",
    "omega3": "Ômega 3",
    "omega6": "Ômega 6",
}

