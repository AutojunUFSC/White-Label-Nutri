"""Popula uma instância com uma empresa de TESTE: configuração, usuários e ingredientes.

    python manage.py seed_demo            # cria o que faltar (idempotente)
    python manage.py seed_demo --resetar  # apaga ingredientes/usuários demo e recria

Só para desenvolvimento local: as senhas são públicas. Recusa rodar com DEBUG=False
(a menos que use --forcar). Valores nutricionais aproximados da TACO, por 100 g — servem
para testar o sistema, não para rótulo real.
"""
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.fichas.models import Chave, Ficha, Ficha_Ingrediente, Ingrediente, Membro
from apps.fichas.servicos import normalizar_100g, obter_tabela, recalcular_tabela
from apps.plataforma.models import ConfiguracaoInstancia

NOME_EMPRESA = "Empresa Demo"
CHAVE = "DEMO-2026"
SENHA = "demo1234"
ORIGEM = "TACO (demo)"

# (usuário, nome, e-mail, administrador?)
USUARIOS = [
    ("admin", "Administrador Demo", "admin@demo.local", True),
    ("nutri", "Nutricionista Demo", "nutri@demo.local", False),
    ("aluno", "Aluno Demo", "aluno@demo.local", False),
]

# nome: (kcal, proteínas, gord. totais, carboidratos, fibras, açúcares totais,
#        gord. sat., gord. trans, colesterol mg, cálcio mg, ferro mg, sódio mg)
INGREDIENTES = {
    "Arroz branco cozido":        (128, 2.5, 0.2, 28.1, 1.6, 0.0, 0.1, 0, 0, 4, 0.1, 1),
    "Arroz integral cozido":      (124, 2.6, 1.0, 25.8, 2.7, 0.0, 0.3, 0, 0, 5, 0.3, 1),
    "Feijão carioca cozido":      (76, 4.8, 0.5, 13.6, 8.5, 0.3, 0.1, 0, 0, 27, 1.3, 2),
    "Macarrão cozido":            (102, 3.4, 0.5, 19.9, 1.4, 0.0, 0.1, 0, 0, 7, 0.4, 1),
    "Pão francês":                (300, 8.0, 3.1, 58.6, 2.3, 2.0, 0.8, 0, 0, 16, 1.0, 648),
    "Aveia em flocos":            (394, 13.9, 8.5, 66.6, 9.1, 1.0, 1.5, 0, 0, 48, 4.4, 5),
    "Farinha de trigo":           (360, 9.8, 1.4, 75.1, 2.3, 0.5, 0.2, 0, 0, 18, 1.0, 1),
    "Farinha de mandioca":        (361, 1.6, 0.3, 87.9, 6.5, 1.0, 0.1, 0, 0, 65, 1.1, 10),
    "Batata inglesa cozida":      (52, 1.2, 0.0, 11.9, 1.3, 0.8, 0.0, 0, 0, 4, 0.2, 2),
    "Cenoura crua":               (34, 1.3, 0.2, 7.7, 3.2, 4.0, 0.0, 0, 0, 23, 0.2, 3),
    "Tomate":                     (15, 1.1, 0.2, 3.1, 1.2, 2.5, 0.0, 0, 0, 7, 0.2, 1),
    "Cebola":                     (39, 1.7, 0.1, 8.9, 2.2, 4.0, 0.0, 0, 0, 14, 0.2, 1),
    "Alho":                       (113, 7.0, 0.2, 23.9, 4.3, 1.0, 0.0, 0, 0, 14, 0.8, 1),
    "Banana prata":               (98, 1.3, 0.1, 26.0, 2.0, 15.0, 0.0, 0, 0, 8, 0.4, 0),
    "Maçã":                       (56, 0.3, 0.0, 15.2, 1.3, 11.0, 0.0, 0, 0, 3, 0.1, 0),
    "Frango, peito grelhado":     (159, 32.0, 2.5, 0.0, 0.0, 0.0, 0.8, 0, 89, 5, 0.3, 50),
    "Carne bovina, patinho":      (219, 35.9, 7.3, 0.0, 0.0, 0.0, 2.9, 0, 80, 5, 3.4, 60),
    "Ovo de galinha cozido":      (146, 13.3, 9.5, 0.6, 0.0, 0.4, 2.9, 0, 397, 49, 1.5, 146),
    "Leite integral":             (62, 2.9, 3.0, 4.5, 0.0, 4.5, 1.9, 0, 10, 123, 0.0, 51),
    "Iogurte natural":            (51, 4.1, 1.7, 5.2, 0.0, 5.2, 1.0, 0, 6, 143, 0.0, 52),
    "Queijo mussarela":           (330, 22.6, 25.2, 3.0, 0.0, 1.0, 14.5, 0, 80, 875, 0.3, 581),
    "Manteiga com sal":           (726, 0.4, 82.4, 0.0, 0.0, 0.0, 51.0, 0, 215, 15, 0.1, 579),
    "Creme de leite":             (221, 1.5, 22.5, 3.4, 0.0, 3.0, 14.0, 0, 70, 55, 0.0, 33),
    "Leite condensado":           (313, 7.7, 6.7, 57.0, 0.0, 56.0, 4.2, 0, 26, 246, 0.2, 100),
    "Açúcar refinado":            (387, 0.3, 0.0, 99.5, 0.0, 99.5, 0.0, 0, 0, 4, 0.1, 0),
    "Sal refinado":               (0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0.0, 38758),
    "Óleo de soja":               (884, 0.0, 100.0, 0.0, 0.0, 0.0, 15.0, 0, 0, 0, 0.0, 0),
    "Azeite de oliva":            (884, 0.0, 100.0, 0.0, 0.0, 0.0, 15.6, 0, 0, 0, 0.0, 0),
    "Chocolate ao leite":         (540, 7.2, 30.3, 59.6, 2.2, 54.0, 18.0, 0, 20, 189, 2.3, 79),
    "Amendoim torrado":           (606, 22.5, 54.0, 18.7, 7.8, 4.0, 8.0, 0, 0, 37, 1.3, 2),
    "Água":                       (0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0.0, 0),
}

# Fichas de exemplo. pesoTotal = peso da preparação pronta (o bolo perde água no forno).
FICHAS = [
    {
        "nomeFicha": "Bolo de chocolate simples", "cliente": "Cliente Demo", "finalizada": True,
        "pesoTotal": 950, "pesoPorcao": 60, "pesoAnvisa": 60, "medCaseiraPorcao": "1 fatia",
        "itens": [
            ("Farinha de trigo", 300), ("Açúcar refinado", 200), ("Ovo de galinha cozido", 150),
            ("Leite integral", 200), ("Óleo de soja", 100), ("Chocolate ao leite", 80),
        ],
    },
    {
        "nomeFicha": "Marmita de arroz, feijão e frango", "cliente": "Cliente Demo",
        "finalizada": False, "pesoTotal": 400, "pesoPorcao": 400, "pesoAnvisa": 400,
        "medCaseiraPorcao": "1 marmita",
        "itens": [
            ("Arroz branco cozido", 150), ("Feijão carioca cozido", 100),
            ("Frango, peito grelhado", 120), ("Azeite de oliva", 10), ("Sal refinado", 1),
        ],
    },
]


class Command(BaseCommand):
    help = "Cria uma empresa de teste com usuários e ingredientes (só desenvolvimento)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--resetar", action="store_true",
            help="Apaga os ingredientes e usuários demo antes de recriar.",
        )
        parser.add_argument(
            "--forcar", action="store_true", help="Permite rodar com DEBUG=False."
        )

    def handle(self, *args, **opcoes):
        if not settings.DEBUG and not opcoes["forcar"]:
            raise CommandError(
                "seed_demo usa senhas públicas e só roda com DEBUG=True. "
                "Use --forcar se tiver certeza."
            )
        if ConfiguracaoInstancia.objects.exclude(nome_exibicao=NOME_EMPRESA).exists():
            raise CommandError(
                "Este banco tem dados de uma empresa real. seed_demo só roda em banco de teste."
            )

        with transaction.atomic():
            if opcoes["resetar"]:
                Ingrediente.objects.filter(origemDosDados=ORIGEM).delete()
                User.objects.filter(username__in=[u[0] for u in USUARIOS]).delete()

            ConfiguracaoInstancia.objects.get_or_create(
                defaults={"nome_exibicao": NOME_EMPRESA, "cor_primaria": "#0f766e"}
            )
            Chave.objects.get_or_create(key=CHAVE)
            grupo, _ = Group.objects.get_or_create(name=settings.GRUPO_ADMINISTRADORES)

            membros = {}
            for username, nome, email, admin in USUARIOS:
                usuario, criado = User.objects.get_or_create(
                    username=username, defaults={"email": email}
                )
                if criado:
                    usuario.set_password(SENHA)
                    usuario.is_staff = usuario.is_superuser = admin
                    usuario.save()
                if admin:
                    usuario.groups.add(grupo)
                membros[username], _ = Membro.objects.get_or_create(
                    usuario=usuario, defaults={"nome": nome, "semestre": "", "email": email}
                )

            novos = 0
            for numero, (nome, v) in enumerate(INGREDIENTES.items(), start=1):
                kcal, prot, gord, carb, fib, acuc, sat, trans, colest, ca, fe, na = v
                _, criado = Ingrediente.objects.get_or_create(
                    nomeIng=nome,
                    origemDosDados=ORIGEM,
                    defaults=self._campos(
                        membros["admin"], numero, kcal, prot, gord, carb, fib, acuc,
                        sat, trans, colest, ca, fe, na,
                    ),
                )
                novos += criado

            for dados in FICHAS:
                self._ficha(membros["nutri"], dados)

        self.stdout.write(self.style.SUCCESS(
            f"Empresa demo pronta: {novos} ingredientes novos "
            f"({Ingrediente.objects.count()} no total), {Ficha.objects.count()} fichas.\n"
            f"  Usuários: {', '.join(u[0] for u in USUARIOS)}  |  senha: {SENHA}\n"
            f"  Chave de cadastro: {CHAVE}"
        ))

    @staticmethod
    def _ficha(autor, dados):
        campos = {k: v for k, v in dados.items() if k != "itens"}
        ficha, criada = Ficha.objects.get_or_create(
            autor=autor, nomeFicha=dados["nomeFicha"], defaults=campos
        )
        if not criada:
            return
        obter_tabela(ficha)
        for nome, peso in dados["itens"]:
            Ficha_Ingrediente.objects.create(
                ficha=ficha, ingrediente=Ingrediente.objects.get(nomeIng=nome, origemDosDados=ORIGEM),
                pesoBruto=peso, pesoLiquido=peso, nomeFantasia=nome[:50],
            )
        recalcular_tabela(ficha)

    @staticmethod
    def _campos(autor, numero, kcal, prot, gord, carb, fib, acuc, sat, trans, colest, ca, fe, na):
        ing = Ingrediente(
            autorIng=autor, nomeIng="", origemDosDados=ORIGEM, addManualmente=False,
            numRef=numero, qtdeDoIngrediente=100,
            energiakcal=kcal, energiaKJ=round(kcal * 4.184, 1), proteinas=prot,
            gordTotais=gord, carboidratos=carb, fibras=fib, acucaresTotais=acuc,
            gordSat=sat, gordTrans=trans, colesterol=colest, calcio=ca, ferro=fe, sodio=na,
        )
        normalizar_100g(ing)
        campos = {
            f.name: getattr(ing, f.name)
            for f in Ingrediente._meta.concrete_fields
            if f.name not in ("id", "nomeIng", "dataCriacao")
        }
        campos["autorIng"] = autor
        return campos
